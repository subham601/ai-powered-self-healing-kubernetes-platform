from __future__ import annotations

import os
from typing import Any

import httpx


class LokiClient:
    """Query logs from Grafana Loki (LogQL)."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        self.base_url = (base_url or os.getenv("LOKI_URL", "")).rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def query_pod_logs(
        self,
        *,
        namespace: str,
        pod: str,
        tail_lines: int = 600,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("Loki is not configured (LOKI_URL empty)")

        # Prefer pod label; fall back to kubernetes pod name field.
        query = (
            f'{{namespace="{namespace}", pod="{pod}"}}'
            f' or {{namespace="{namespace}", pod_name="{pod}"}}'
        )
        params: dict[str, Any] = {
            "query": query,
            "limit": tail_lines,
            "direction": "backward",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/loki/api/v1/query_range",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        lines: list[str] = []
        for stream in data.get("data", {}).get("result", []):
            for _ts, line in stream.get("values", []):
                lines.append(line)
        # Loki returns newest-first when direction=backward.
        lines.reverse()
        return "\n".join(lines[-tail_lines:])
