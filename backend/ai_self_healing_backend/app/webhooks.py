from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_analyzer: Any | None = None
_remediator: Any | None = None


def configure_webhooks(*, analyzer: Any, remediator: Any) -> None:
    global _analyzer, _remediator
    _analyzer = analyzer
    _remediator = remediator


class AlertmanagerAlert(BaseModel):
    status: str = "firing"
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)


class AlertmanagerPayload(BaseModel):
    status: str = "firing"
    alerts: list[AlertmanagerAlert] = Field(default_factory=list)


def _label(alert: AlertmanagerAlert, key: str, default: str = "") -> str:
    return alert.labels.get(key) or alert.annotations.get(key) or default


@router.post("/alerts")
def alertmanager_webhook(payload: AlertmanagerPayload):
    """
    Alertmanager webhook -> analyze + optional auto-heal.

    Expected alert labels:
      - namespace
      - deployment (or pod)
      - workload_kind (deployment|pod, optional)
    """
    if _analyzer is None or _remediator is None:
        raise HTTPException(status_code=503, detail="Webhooks not configured")

    auto_heal = os.getenv("SELF_HEAL_ALERT_AUTO_HEAL", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    dry_run = os.getenv("SELF_HEAL_ALERT_DRY_RUN", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    results: list[dict[str, Any]] = []
    for alert in payload.alerts:
        if alert.status != "firing":
            continue

        namespace = _label(alert, "namespace")
        deployment = _label(alert, "deployment") or _label(alert, "pod")
        workload_kind = _label(alert, "workload_kind", "deployment")

        if not namespace or not deployment:
            results.append(
                {
                    "skipped": True,
                    "reason": "missing_namespace_or_workload_labels",
                    "labels": alert.labels,
                }
            )
            continue

        try:
            analysis = _analyzer.analyze(
                namespace=namespace,
                workload=deployment,
                workload_kind=workload_kind,
            )
            out: dict[str, Any] = {"analysis": analysis, "alert_labels": alert.labels}
            if auto_heal:
                out["remediation"] = _remediator.remediate(
                    namespace=namespace,
                    workload=deployment,
                    workload_kind=workload_kind,
                    recommendation=analysis,
                    dry_run=dry_run,
                )
            results.append(out)
        except Exception as e:
            results.append(
                {
                    "error": str(e),
                    "namespace": namespace,
                    "workload": deployment,
                }
            )

    if not results:
        raise HTTPException(status_code=400, detail="No firing alerts to process")
    return {"processed": len(results), "results": results}
