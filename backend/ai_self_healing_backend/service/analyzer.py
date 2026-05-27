from __future__ import annotations

import asyncio
from typing import Any


from ai_self_healing_backend.ai.provider import AIProvider
from ai_self_healing_backend.k8s.client import KubernetesClient
from ai_self_healing_backend.service.ai_json import extract_json_object
from ai_self_healing_backend.service.log_collector import LogCollector
from ai_self_healing_backend.service.log_parsing import (
    extract_signals,
    heuristic_confidence,
    recommended_action_from_signals,
)
from ai_self_healing_backend.service.models import AIAction, AIAnalysis, IncidentPacket


class LogAnalyzer:
    def __init__(self, k8s: KubernetesClient, ai: AIProvider):
        self.k8s = k8s
        self.ai = ai
        self.logs = LogCollector(k8s=k8s)

    def analyze(
        self,
        namespace: str,
        workload: str,
        workload_kind: str,
        tail_lines: int = 600,
        confidence_threshold: str = "medium",
    ) -> dict[str, Any]:
        logs, log_source = self.logs.collect(
            namespace=namespace,
            workload=workload,
            workload_kind=workload_kind,
            tail_lines=tail_lines,
        )

        # Hybrid approach:
        # 1) deterministic parsing -> signals + heuristic confidence
        # 2) optional LLM -> structured JSON extract
        heuristic_signals = extract_signals(logs)
        heuristic_conf = heuristic_confidence(heuristic_signals)

        llm_json: dict[str, Any] | None = None
        llm_conf: str | None = None
        llm_root_cause: str | None = None
        llm_fix: str | None = None  # unused; kept for backward compatibility
        llm_signals: list[str] | None = None
        llm_remediation: dict[str, Any] | None = None  # unused; kept for backward compatibility


        ai_resp = asyncio.run(self.ai.analyze_text(logs))


        # We use the heuristic fields from AIProvider for signals/root_cause,
        # but if the provider returned a JSON-like response inside root_cause,
        # we attempt to extract it.
        if isinstance(getattr(ai_resp, "root_cause", None), str):
            maybe = extract_json_object(ai_resp.root_cause)
            if maybe:
                llm_json = maybe


        if llm_json:
            try:
                llm_conf = llm_json.get("confidence")
                llm_root_cause = llm_json.get("root_cause")
                llm_fix = llm_json.get("fix")
                llm_signals = llm_json.get("signals")
                llm_remediation = llm_json.get("remediation")
            except Exception:
                llm_json = None

        # Confidence gating - hybrid:
        # - if LLM confidence missing/invalid -> use heuristic confidence
        final_conf = heuristic_conf
        if llm_json and isinstance(llm_conf, str) and llm_conf in ("low", "medium", "high"):
            final_conf = llm_conf

        final_signals = heuristic_signals
        if llm_json and isinstance(llm_signals, list) and llm_signals:
            final_signals = [str(s) for s in llm_signals]

        # Recommended fix + remediation:
        # Prefer LLM fix/remediation when present and valid.
        _default_fix, default_action_params = (
            recommended_action_from_signals(final_signals)
        )
        llm_action: AIAction | None = None
        llm_fix_text: str | None = None

        if llm_json:
            candidate_fix = llm_json.get("fix")
            llm_fix_text = (
                candidate_fix
                if isinstance(candidate_fix, str)
                else None
            )

            rem = llm_json.get("remediation")
            if isinstance(rem, dict):
                action_type = rem.get("type")
                params = rem.get("parameters", {})
                if isinstance(action_type, str) and isinstance(params, dict):
                    llm_action = AIAction(type=action_type, parameters=params)

        default_reason = default_action_params.get("reason", "")
        final_fix = llm_fix_text or f"Heuristic analysis: {default_reason}"

        if llm_action is None:
            # Map heuristic to a conservative single action.
            inferred_type, inferred_params = recommended_action_from_signals(final_signals)
            llm_action = AIAction(type=inferred_type, parameters=inferred_params)

        # Root cause: prefer LLM/root_cause when it looks like content.
        final_root_cause = (
            llm_root_cause
            or getattr(ai_resp, "root_cause", None)
            or "Failure signals detected in logs."
        )

        # Build strict AIAnalysis + IncidentPacket.
        analysis = AIAnalysis(
            root_cause=str(final_root_cause),
            confidence=final_conf,  # type: ignore[arg-type]
            signals=final_signals,
            fix=final_fix,
            remediation=llm_action,
        )

        packet = IncidentPacket(
            namespace=namespace,
            workload=workload,
            workload_kind=workload_kind,
            tail_lines=tail_lines,
            analysis=analysis,
            evidence={
                "log_source": log_source,
                "heuristic_confidence": heuristic_conf,
                "ai_provider_severity": getattr(ai_resp, "severity", None),
                "signals_heuristic": heuristic_signals,
                "signals_final": final_signals,
            },
        )

        # Add gating outcome for remediator.
        if confidence_threshold == "medium":
            confidence_ok = final_conf in ("high", "medium")
        else:
            confidence_ok = final_conf == "high"


        # Conservative: if gating fails, we still return analysis but with a noop remediation.
        if not confidence_ok:
            analysis.remediation = AIAction(type="noop", parameters={"reason": "Confidence below threshold"})

        return packet.model_dump()


