from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import httpx

from ai_self_healing_backend.k8s.client import KubernetesClient


@dataclass(frozen=True)
class LogCollectorResult:
    logs: str
    log_source: str


class LogCollector:
    """
    Collect logs for a workload.

    Preference order:
      1) Loki (when configured)
      2) Kubernetes pod logs/events fallback

    Returns:
      (logs_text, log_source)
    """

    def __init__(self, *, k8s: KubernetesClient):
        self.k8s = k8s

        loki_base_url = os.getenv("LOKI_BASE_URL", "")
        self._loki_base_url = loki_base_url.strip().rstrip("/")

        self._loki_query_limit = int(os.getenv("LOKI_QUERY_LIMIT", "2000"))

        # Loki labels are produced by promtail; keep them configurable.
        self._loki_namespace_label = os.getenv(
            "LOKI_NAMESPACE_LABEL", "namespace"
        )
        self._loki_app_label = os.getenv("LOKI_APP_LABEL", "app")
        self._loki_workload_kind_label = os.getenv(
            "LOKI_WORKLOAD_KIND_LABEL", "workload_kind"
        )
        self._loki_workload_name_label = os.getenv(
            "LOKI_WORKLOAD_NAME_LABEL", "workload"
        )

    async def collect(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        tail_lines: int = 600,
    ) -> Tuple[str, str]:
        if self._loki_base_url:
            try:
                logs = await self._collect_from_loki(
                    namespace=namespace,
                    workload=workload,
                    workload_kind=workload_kind,
                    tail_lines=tail_lines,
                )
                if logs.strip():
                    return logs, "loki"
            except Exception:
                # Fallback silently to Kubernetes
                pass

        logs = await self._collect_from_k8s(
            namespace=namespace,
            workload=workload,
            workload_kind=workload_kind,
            tail_lines=tail_lines,
        )
        return logs, "kubernetes"

    async def _collect_from_loki(
        self,
        *,
        namespace: str,
        workload: str,
        workload_kind: str,
        tail_lines: int,
    ) -> str:
        label_ns = f'{self._loki_namespace_label}="{namespace}"'
        label_workload = f'{self._loki_workload_name_label}="{workload}"'
        label_kind = (
            f'{self._loki_workload_kind_label}="{workload_kind}"'
        )
        label_app = f'{self._loki_app_label}="{workload}"'

        selectors = [
            f"{{{label_ns},{label_workload},{label_kind}}}",
            f"{{{label_ns},{label_workload}}}",
            f"{{{label_ns},{label_app}}}",
            f"{{{label_ns}}}",
        ]

        max_points = min(self._loki_query_limit, max(1, tail_lines))
        url = f"{self._loki_base_url}/loki/api/v1/query_range"

        minutes = float(os.getenv("LOKI_LOOKBACK_MINUTES", "15"))
        now_sec = time.time()
        now_ns = int(now_sec * 1e9)

        lookback_ns = int(minutes * 60 * 1e9)
        start_ns = now_ns - lookback_ns
        params_base: dict[str, Any] = {
            "limit": max_points,
            "start": start_ns,
            "end": now_ns,
        }

        last_exc: Optional[Exception] = None
        for selector in selectors:
            query = f'{selector} |~ ".*"'
            params = {**params_base, "query": query}

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()

            result = payload.get("data", {}).get("result", [])
            lines: list[str] = []
            for stream in result:
                for _ts, line in stream.get("values", []):
                    if isinstance(line, str):
                        lines.append(line)

            if lines:
                return "\n".join(lines[-tail_lines:])

        if last_exc:
            raise last_exc
        return ""

    async def _collect_from_k8s(
        self,
        *,
        namespace: str,
        workload: str,
        workload_kind: str,
        tail_lines: int,
    ) -> str:
        pod_name: Optional[str]
        if workload_kind == "pod":
            pod_name = workload
        else:
            pod_name = self.k8s.get_representative_pod_name(
                namespace=namespace,
                deployment_name=workload,
            )

        if not pod_name:
            return self.k8s.get_pod_events(
                namespace=namespace,
                workload=workload,
            )

        logs = self.k8s.read_pod_logs(
            namespace=namespace,
            pod_name=pod_name,
            tail_lines=tail_lines,
        )
        return logs if logs is not None else ""
