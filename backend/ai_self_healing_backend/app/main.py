from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_self_healing_backend.ai.provider import AIProvider
from ai_self_healing_backend.app.webhooks import configure_webhooks, router as webhooks_router
from ai_self_healing_backend.k8s.client import KubernetesClient
from ai_self_healing_backend.service.analyzer import LogAnalyzer
from ai_self_healing_backend.service.remediator import Remediator

app = FastAPI(
    title="AI Self-Healing Backend",
    version="1.0.0",
    description="ChatOps + automated remediation for Kubernetes workloads",
)

_cors = os.getenv("CORS_ALLOW_ORIGINS", "")
if _cors:
    origins = [o.strip() for o in _cors.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

k8s = KubernetesClient()
ai = AIProvider()
analyzer = LogAnalyzer(k8s=k8s, ai=ai)
remediator = Remediator(k8s=k8s, ai=ai)
configure_webhooks(analyzer=analyzer, remediator=remediator)
app.include_router(webhooks_router)


class AnalyzeRequest(BaseModel):
    namespace: str = Field(..., description="Kubernetes namespace")
    workload: str = Field(
        ...,
        description="Pod name, or deployment name when workload_kind=deployment",
    )
    workload_kind: str = Field(
        "deployment",
        description="pod|deployment (deployment resolves to a representative pod)",
    )
    tail_lines: int = Field(600, ge=1, le=5000)
    auto_heal: bool = Field(False, description="If true, apply remediation actions")
    dry_run: bool = Field(True, description="Never execute changes when true")


class RestartRequest(BaseModel):
    namespace: str
    workload: str
    workload_kind: str = "deployment"
    dry_run: bool = True


class RollbackRequest(BaseModel):
    namespace: str
    workload: str
    workload_kind: str = "deployment"
    dry_run: bool = True


class ScaleRequest(BaseModel):
    namespace: str
    workload: str
    workload_kind: str = "deployment"
    replicas: int = Field(..., ge=0, le=1000)
    dry_run: bool = True


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Analyze workload logs (Loki or Kubernetes API) and optionally auto-heal."""
    try:
        result = analyzer.analyze(
            namespace=req.namespace,
            workload=req.workload,
            workload_kind=req.workload_kind,
            tail_lines=req.tail_lines,
        )
        if req.auto_heal:
            result["remediation"] = remediator.remediate(
                namespace=req.namespace,
                workload=req.workload,
                workload_kind=req.workload_kind,
                recommendation=result,
                dry_run=req.dry_run,
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/restart")
def restart(req: RestartRequest):
    try:
        return remediator.restart(
            namespace=req.namespace,
            workload=req.workload,
            workload_kind=req.workload_kind,
            dry_run=req.dry_run,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/rollback")
def rollback(req: RollbackRequest):
    try:
        return remediator.rollback(
            namespace=req.namespace,
            workload=req.workload,
            workload_kind=req.workload_kind,
            dry_run=req.dry_run,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/scale")
def scale(req: ScaleRequest):
    try:
        return remediator.scale(
            namespace=req.namespace,
            workload=req.workload,
            workload_kind=req.workload_kind,
            replicas=req.replicas,
            dry_run=req.dry_run,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
