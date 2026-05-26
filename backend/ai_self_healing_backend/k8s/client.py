from __future__ import annotations

import os
from kubernetes import client, config


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

