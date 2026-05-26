from __future__ import annotations

from ai_self_healing_backend.ai.provider import AIProvider
from ai_self_healing_backend.k8s.client import KubernetesClient


class LogAnalyzer:
    def __init__(self, k8s: KubernetesClient, ai: AIProvider):
        self.k8s = k8s
        self.ai = ai

    def analyze(self, namespace: str, workload: str, workload_kind: str, tail_lines: int = 600):
        # Scaffold: only pod logs supported. Production should resolve workload->pod list.
        if workload_kind != "pod":
            workload_kind = "pod"

        logs = self.k8s.get_pod_logs(namespace=namespace, pod_name=workload, tail_lines=tail_lines)

        # AIProvider is async but we keep sync call in scaffold
        import asyncio

        ai_resp = asyncio.get_event_loop().run_until_complete(self.ai.analyze_text(logs))

        return {
            "workload": workload,
            "namespace": namespace,
            "workload_kind": workload_kind,
            "severity": ai_resp.severity,
            "signals": ai_resp.signals,
            "root_cause": ai_resp.root_cause,
            "recommendations": ai_resp.recommendations,
        }

