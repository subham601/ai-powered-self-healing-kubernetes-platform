from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kubernetes.client import V1ConfigMap
from kubernetes.client.rest import ApiException

from ai_self_healing_backend.k8s.client import KubernetesClient


@dataclass(frozen=True)
class AuditDecision:
    incident_id: str
    workload: str
    namespace: str
    action: str  # restart|rollback|scale
    confidence: str  # low|medium|high
    status: str  # PENDING|SUCCESS|FAILED
    timestamp: str


class AuditPersistenceFailed(RuntimeError):
    """Fail-closed error raised when the audit ledger cannot persist the decision."""


class AuditLedger:
    """
    ConfigMap-backed audit ledger.

    Design:
    - Each incident is stored under a unique ConfigMap data key: incident-<incident_id>
    - Writing uses a merge-style patch with only that single key, preserving all other incidents
    - Retry is bounded (max 3) for audit persistence (fail-closed on pending write)
    """

    def __init__(self, *, k8s: KubernetesClient):
        self._k8s = k8s
        self._ledger_namespace = os.getenv("SELF_HEAL_LEDGER_NAMESPACE", "ai-healing-system")
        self._ledger_configmap_name = os.getenv(
            "SELF_HEAL_LEDGER_CONFIGMAP", "ai-self-healing-audit-ledger"
        )
        self._incident_key_prefix = os.getenv("SELF_HEAL_LEDGER_KEY_PREFIX", "incident-")

    def _now_ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _incident_key(self, incident_id: str) -> str:
        return f"{self._incident_key_prefix}{incident_id}"

    def _serialize(self, decision: AuditDecision) -> str:
        # Ensure stable JSON (useful for debugging/diffing).
        return json.dumps(
            {
                "incident_id": decision.incident_id,
                "workload": decision.workload,
                "namespace": decision.namespace,
                "action": decision.action,
                "confidence": decision.confidence,
                "status": decision.status,
                "timestamp": decision.timestamp,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def _patch_key(self, *, key: str, value: str) -> None:
        # Patch only one key to avoid overwriting other incident entries.
        patch_body = {"data": {key: value}}
        self._k8s.core.patch_namespaced_config_map(
            name=self._ledger_configmap_name, namespace=self._ledger_namespace, body=patch_body
        )

    def _create_configmap(self, *, key: str, value: str) -> None:
        cm = V1ConfigMap(metadata={"name": self._ledger_configmap_name}, data={key: value})
        self._k8s.core.create_namespaced_config_map(namespace=self._ledger_namespace, body=cm)

    def write_pending(
        self,
        *,
        workload: str,
        namespace: str,
        action: str,
        confidence: str,
        incident_id: str | None = None,
        max_retries: int = 3,
    ) -> str:
        incident_id = incident_id or uuid.uuid4().hex

        decision = AuditDecision(
            incident_id=incident_id,
            workload=workload,
            namespace=namespace,
            action=action,
            confidence=confidence,
            status="PENDING",
            timestamp=self._now_ts(),
        )
        value = self._serialize(decision)
        key = self._incident_key(incident_id)

        last_exc: Exception | None = None
        for _attempt in range(max_retries):
            try:
                try:
                    self._patch_key(key=key, value=value)
                    return incident_id
                except ApiException as e:
                    if e.status == 404:
                        self._create_configmap(key=key, value=value)
                        return incident_id
                    if e.status == 409:
                        # ConfigMap created concurrently, retry patch.
                        continue
                    raise
            except Exception as e:
                last_exc = e
                time.sleep(0.2)

        raise AuditPersistenceFailed(
            f"audit persistence failed: could not write pending decision (incident_id={incident_id})"
        ) from last_exc

    def update_status(
        self,
        *,
        incident_id: str,
        workload: str,
        namespace: str,
        action: str,
        confidence: str,
        status: str,  # SUCCESS|FAILED
        max_retries: int = 3,
    ) -> None:
        decision = AuditDecision(
            incident_id=incident_id,
            workload=workload,
            namespace=namespace,
            action=action,
            confidence=confidence,
            status=status,
            timestamp=self._now_ts(),
        )
        value = self._serialize(decision)
        key = self._incident_key(incident_id)

        last_exc: Exception | None = None
        for _attempt in range(max_retries):
            try:
                try:
                    self._patch_key(key=key, value=value)
                    return
                except ApiException as e:
                    if e.status == 404:
                        self._create_configmap(key=key, value=value)
                        return
                    if e.status == 409:
                        continue
                    raise
            except Exception as e:
                last_exc = e
                time.sleep(0.2)

        raise AuditPersistenceFailed(
            f"audit persistence failed: could not update decision status to {status} (incident_id={incident_id})"
        ) from last_exc

