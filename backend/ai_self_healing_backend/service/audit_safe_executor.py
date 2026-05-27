from __future__ import annotations

from typing import Any, Callable

from ai_self_healing_backend.service.audit_ledger import AuditLedger, AuditPersistenceFailed


class AuditSafeExecutor:
    """
    Enforces production safety around Kubernetes mutations:
    - Step 1: persist audit decision as PENDING (retry-bounded, fail-closed)
    - Step 2: execute the Kubernetes mutation
    - Step 3: persist audit decision as SUCCESS or FAILED
    """

    def __init__(self, *, ledger: AuditLedger, max_audit_retries: int = 3):
        self._ledger = ledger
        self._max_audit_retries = max_audit_retries

    def execute(
        self,
        *,
        action: str,  # restart|rollback|scale
        namespace: str,
        workload: str,
        confidence: str,  # low|medium|high
        execute_fn: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        incident_id = self._ledger.write_pending(
            workload=workload,
            namespace=namespace,
            action=action,
            confidence=confidence,
            max_retries=self._max_audit_retries,
        )

        try:
            result = execute_fn()
            self._ledger.update_status(
                incident_id=incident_id,
                workload=workload,
                namespace=namespace,
                action=action,
                confidence=confidence,
                status="SUCCESS",
                max_retries=self._max_audit_retries,
            )
            # Attach for end-to-end traceability (does not change audit semantics).
            return {**result, "incident_id": incident_id}
        except Exception as e:
            # Best effort audit transition to FAILED (must preserve fail-closed: the mutation already happened).
            try:
                self._ledger.update_status(
                    incident_id=incident_id,
                    workload=workload,
                    namespace=namespace,
                    action=action,
                    confidence=confidence,
                    status="FAILED",
                    max_retries=self._max_audit_retries,
                )
            except AuditPersistenceFailed:
                # If status update fails, we re-raise the original execution error.
                pass
            raise e

