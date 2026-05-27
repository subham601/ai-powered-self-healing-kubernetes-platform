
import time
from typing import Any

from ai_self_healing_backend.ai.provider import AIProvider
from ai_self_healing_backend.k8s.client import KubernetesClient
from ai_self_healing_backend.k8s.executor import K8sExecutor
from ai_self_healing_backend.service.audit_ledger import AuditLedger, AuditPersistenceFailed
from ai_self_healing_backend.service.audit_safe_executor import AuditSafeExecutor


class Remediator:
    def __init__(self, k8s: KubernetesClient, ai: AIProvider):
        self.k8s = k8s
        self.ai = ai
        # Executor uses the official client APIs.
        self.executor = K8sExecutor(apps_api=self.k8s.apps, core_api=self.k8s.core)
        # Final safety layer: fail-closed audit ledger + guarded execution.
        self.audit_ledger = AuditLedger(k8s=self.k8s)
        self.audit_safe_executor = AuditSafeExecutor(ledger=self.audit_ledger)



    def _guardrails(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        recommendation: dict[str, Any],
        dry_run: bool,
    ) -> tuple[bool, dict[str, Any]]:
        # Guardrails (scaffolded but enforced):
        # - allow only namespace/workload_kind if explicitly allowed via env
        # - require confidence >= medium for auto-heal
        max_retries = int(
            __import__("os").getenv("SELF_HEAL_MAX_RETRIES", "3")
        )
        cooldown_seconds = int(
            __import__("os").getenv("SELF_HEAL_COOLDOWN_SECONDS", "300")
        )
        allowed_namespaces = set(
            __import__("os").getenv("SELF_HEAL_ALLOWED_NAMESPACES", "ai-healing-system").split(",")
        )

        if dry_run:
            return True, {"reason": "dry_run"}

        if namespace not in allowed_namespaces:
            return False, {"reason": "namespace_not_allowed"}

        analysis = recommendation.get("analysis") or {}
        confidence = analysis.get("confidence")
        action = (analysis.get("remediation") or {}).get("type")

        if action == "noop":
            return False, {"reason": "noop_action"}

        if confidence not in ("medium", "high"):
            return False, {"reason": "confidence_too_low"}

        # Basic infinite-loop prevention:
        # Use a process-local cooldown registry keyed by namespace/workload.
        key = f"{namespace}/{workload}"
        now = time.time()
        last_key = f"_selfheal_last_{key}"
        attempts_key = f"_selfheal_attempts_{key}"

        # store on instance dict
        if not hasattr(self, "_guard_state"):
            self._guard_state = {}
        state = self._guard_state

        last_ts = state.get(last_key, 0)
        attempts = int(state.get(attempts_key, 0))

        if attempts >= max_retries:
            return False, {"reason": "max_retries_exceeded", "attempts": attempts}
        if now - last_ts < cooldown_seconds:
            return False, {"reason": "cooldown_active", "seconds_left": int(cooldown_seconds - (now - last_ts))}

        # Mark attempt (reserved)
        state[last_key] = now
        state[attempts_key] = attempts + 1
        return True, {"reason": "guardrails_ok"}

    def remediate(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        recommendation: dict,
        dry_run: bool,
    ) -> dict[str, Any]:
        guard_ok, guard_info = self._guardrails(
            namespace=namespace,
            workload=workload,
            workload_kind=workload_kind,
            recommendation=recommendation,
            dry_run=dry_run,
        )

        planned_actions: list[dict[str, Any]] = []

        action = (recommendation.get("analysis") or {}).get("remediation") or {}
        action_type = action.get("type")
        action_params = action.get("parameters") or {}
        analysis = recommendation.get("analysis") or {}
        confidence = analysis.get("confidence") or "high"

        if not guard_ok:
            return {
                "dry_run": dry_run,
                "planned_actions": [],
                "ai_summary": {
                    "confidence": (recommendation.get("analysis") or {}).get("confidence"),
                    "root_cause": (recommendation.get("analysis") or {}).get("root_cause"),
                },
                "guardrails": {"allowed": False, **guard_info},
            }

        # Execute safe actions.
        # All K8s mutations must go through these methods so guardrails stay centralized.
        if action_type == "restart":
            planned_actions.append(
                self.restart(
                    namespace=namespace,
                    workload=workload,
                    workload_kind=workload_kind,
                    dry_run=dry_run,
                    confidence=str(confidence),
                )
            )
        elif action_type == "scale":
            replicas = int(action_params.get("replicas", 0))
            if replicas <= 0:
                # Conservative default
                replicas = 1
            planned_actions.append(
                self.scale(
                    namespace=namespace,
                    workload=workload,
                    workload_kind=workload_kind,
                    replicas=replicas,
                    dry_run=dry_run,
                    confidence=str(confidence),
                )
            )
        elif action_type == "rollback":
            planned_actions.append(
                self.rollback(
                    namespace=namespace,
                    workload=workload,
                    workload_kind=workload_kind,
                    dry_run=dry_run,
                    confidence=str(confidence),
                )
            )
        else:
            planned_actions.append(
                {"action": "noop", "dry_run": dry_run, "reason": "unknown_action"}
            )

        # Fail-closed safety layer:
        # If audit persistence failed, Remediator must stop and return the audit_blocked response.
        if planned_actions and planned_actions[0].get("audit_blocked") is True:
            return {"audit_blocked": True, "reason": "audit_persistence_failed"}

        return {
            "dry_run": dry_run,
            "planned_actions": planned_actions,
            "ai_summary": {
                "confidence": (recommendation.get("analysis") or {}).get("confidence"),
                "root_cause": (recommendation.get("analysis") or {}).get("root_cause"),
            },
            "guardrails": {"allowed": True, **guard_info},
        }

    def restart(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        dry_run: bool,
        confidence: str = "high",
    ) -> dict[str, Any]:
        if workload_kind != "deployment":
            return {
                "action": "restart",
                "namespace": namespace,
                "workload": workload,
                "workload_kind": workload_kind,
                "dry_run": dry_run,
                "reason": "unsupported_workload_kind",
            }

        if dry_run:
            return {
                "action": "restart",
                "namespace": namespace,
                "deployment": workload,
                "workload_kind": workload_kind,
                "dry_run": True,
            }

        try:
            return self.audit_safe_executor.execute(
                action="restart",
                namespace=namespace,
                workload=workload,
                confidence=confidence,
                execute_fn=lambda: self.executor.restart_deployment(namespace, workload),
            )
        except AuditPersistenceFailed:
            return {"audit_blocked": True, "reason": "audit_persistence_failed"}


    def rollback(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        dry_run: bool,
        confidence: str = "high",
    ) -> dict[str, Any]:
        if workload_kind != "deployment":
            return {
                "action": "rollback",
                "namespace": namespace,
                "workload": workload,
                "workload_kind": workload_kind,
                "dry_run": dry_run,
                "reason": "unsupported_workload_kind",
            }

        if dry_run:
            return {
                "action": "rollback",
                "namespace": namespace,
                "deployment": workload,
                "workload_kind": workload_kind,
                "dry_run": True,
            }

        try:
            return self.audit_safe_executor.execute(
                action="rollback",
                namespace=namespace,
                workload=workload,
                confidence=confidence,
                execute_fn=lambda: self.executor.rollback_deployment(namespace, workload),
            )
        except AuditPersistenceFailed:
            return {"audit_blocked": True, "reason": "audit_persistence_failed"}


    def scale(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        replicas: int,
        dry_run: bool,
        confidence: str = "high",
    ) -> dict[str, Any]:
        if workload_kind != "deployment":
            return {
                "action": "scale",
                "namespace": namespace,
                "workload": workload,
                "workload_kind": workload_kind,
                "replicas": replicas,
                "dry_run": dry_run,
                "reason": "unsupported_workload_kind",
            }

        if dry_run:
            return {
                "action": "scale",
                "namespace": namespace,
                "deployment": workload,
                "workload_kind": workload_kind,
                "replicas": replicas,
                "dry_run": True,
            }

        try:
            return self.audit_safe_executor.execute(
                action="scale",
                namespace=namespace,
                workload=workload,
                confidence=confidence,
                execute_fn=lambda: self.executor.scale_deployment(
                    namespace, workload, replicas
                ),
            )
        except AuditPersistenceFailed:
            return {"audit_blocked": True, "reason": "audit_persistence_failed"}



