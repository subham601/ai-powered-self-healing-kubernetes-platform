from __future__ import annotations

import time
from typing import Any

from kubernetes import client


class K8sExecutor:
    """Low-level Kubernetes execution helpers.

    Notes:
    - This class performs actual mutations.
    - Guardrails and confidence gating must happen before calling these.
    """

    def __init__(self, apps_api: client.AppsV1Api, core_api: client.CoreV1Api):
        self.apps = apps_api
        self.core = core_api

    def restart_deployment(self, namespace: str, deployment_name: str) -> dict[str, Any]:
        # Rollout restart is implemented by updating pod template annotations.
        ts = str(int(time.time()))
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "ai-self-healing/restarted-at": ts
                        }
                    }
                }
            }
        }
        self.apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=patch,
        )
        return {
            "action": "restart",
            "namespace": namespace,
            "deployment": deployment_name,
            "restarted_at": ts,
        }

    def scale_deployment(
        self, namespace: str, deployment_name: str, replicas: int
    ) -> dict[str, Any]:
        patch = {"spec": {"replicas": int(replicas)}}
        self.apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=patch,
        )
        return {
            "action": "scale",
            "namespace": namespace,
            "deployment": deployment_name,
            "replicas": int(replicas),
        }

    def get_deployment_current_revision(self, namespace: str, deployment_name: str) -> tuple[str, str]:
        dep = self.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        status = dep.status
        annotations = (dep.spec.template.metadata.annotations or {}) if dep.spec and dep.spec.template else {}
        revision = annotations.get(
            "deployment.kubernetes.io/revision", ""
        )
        # We also expose observedGeneration for debugging.
        return (revision, str(getattr(status, "observed_generation", "")))

    def rollback_deployment(self, namespace: str, deployment_name: str) -> dict[str, Any]:
        # Rollback by selecting the previous ReplicaSet owned by this deployment.
        dep = self.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        selector = dep.spec.selector.match_labels or {}
        # Match labels to list ReplicaSets.
        label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])

        rsets = self.apps.list_namespaced_replica_set(namespace=namespace, label_selector=label_selector)
        items = list(rsets.items or [])

        def rs_revision(rs: client.V1ReplicaSet) -> int:
            ann = (rs.metadata.annotations or {}) if rs.metadata and rs.metadata.annotations else {}
            try:
                return int(ann.get("deployment.kubernetes.io/revision", "0"))
            except Exception:
                return 0

        # Filter to RS created by this deployment (best-effort) via ownerRefs.
        owned: list[client.V1ReplicaSet] = []
        for rs in items:
            owners = rs.metadata.owner_references or []
            if any(
                (o.kind == "Deployment" and o.name == deployment_name)
                for o in owners
            ):
                owned.append(rs)

        if not owned:
            # Fallback: choose best-effort by highest revision.
            owned = items

        owned.sort(key=rs_revision)
        if len(owned) < 2:
            raise RuntimeError("Not enough ReplicaSet history to rollback")

        current_rs = owned[-1]
        previous_rs = owned[-2]

        # Patch deployment pod template to match previous RS template.
        prev_template = previous_rs.spec.template
        patch = {"spec": {"template": prev_template.model_dump() if hasattr(prev_template, 'model_dump') else prev_template.to_dict()}}

        self.apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=patch,
        )

        return {
            "action": "rollback",
            "namespace": namespace,
            "deployment": deployment_name,
            "from_revision": rs_revision(current_rs),
            "to_revision": rs_revision(previous_rs),
        }

