from __future__ import annotations

from kubernetes import client, config
from kubernetes.client import V1Pod


class KubernetesClient:
    def __init__(self):
        # Prefer in-cluster, fallback to local kubeconfig
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()

    def get_pod_logs(self, namespace: str, pod_name: str, tail_lines: int = 600) -> str:
        return self.core.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            timestamps=False,
            _preload_content=True,
        )

    def list_pods_for_deployment(self, namespace: str, deployment_name: str) -> list[V1Pod]:
        dep = self.apps.read_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )
        selector = dep.spec.selector.match_labels or {}
        label_selector = ",".join(f"{k}={v}" for k, v in selector.items())
        pods = self.core.list_namespaced_pod(
            namespace=namespace, label_selector=label_selector
        )
        return list(pods.items or [])

    def _pick_pod(self, pods: list[V1Pod]) -> str:
        if not pods:
            raise RuntimeError("No pods found for workload")

        def restart_count(pod: V1Pod) -> int:
            total = 0
            for cs in pod.status.container_statuses or []:
                total += int(cs.restart_count or 0)
            return total

        # Prefer pods with restarts (likely failing), else newest by name.
        pods_sorted = sorted(pods, key=restart_count, reverse=True)
        pod = pods_sorted[0]
        if not pod.metadata or not pod.metadata.name:
            raise RuntimeError("Pod missing metadata.name")
        return pod.metadata.name

    def resolve_pod_for_workload(
        self, *, namespace: str, workload: str, workload_kind: str
    ) -> str:
        kind = (workload_kind or "pod").lower()
        if kind == "deployment":
            pods = self.list_pods_for_deployment(namespace, workload)
            return self._pick_pod(pods)
        if kind == "pod":
            return workload
        raise ValueError(f"Unsupported workload_kind for logs: {workload_kind}")
