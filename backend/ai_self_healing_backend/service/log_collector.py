from __future__ import annotations

from ai_self_healing_backend.k8s.client import KubernetesClient
from ai_self_healing_backend.k8s.loki_client import LokiClient


class LogCollector:
    """Collect workload logs from Loki (preferred) or Kubernetes API."""

    def __init__(self, k8s: KubernetesClient, loki: LokiClient | None = None):
        self.k8s = k8s
        self.loki = loki or LokiClient()

    def collect(
        self,
        *,
        namespace: str,
        workload: str,
        workload_kind: str,
        tail_lines: int = 600,
    ) -> tuple[str, str]:
        """
        Returns (logs, source) where source is 'loki' or 'kubernetes'.
        """
        pod_name = self.k8s.resolve_pod_for_workload(
            namespace=namespace,
            workload=workload,
            workload_kind=workload_kind,
        )

        if self.loki.enabled:
            try:
                logs = self.loki.query_pod_logs(
                    namespace=namespace,
                    pod=pod_name,
                    tail_lines=tail_lines,
                )
                if logs.strip():
                    return logs, "loki"
            except Exception:
                pass

        logs = self.k8s.get_pod_logs(
            namespace=namespace,
            pod_name=pod_name,
            tail_lines=tail_lines,
        )
        return logs, "kubernetes"
