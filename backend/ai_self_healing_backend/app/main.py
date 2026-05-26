from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_self_healing_backend.k8s.client import KubernetesClient
from ai_self_healing_backend.ai.provider import AIProvider
from ai_self_healing_backend.service.analyzer import LogAnalyzer
from ai_self_healing_backend.service.remediator import Remediator


app = FastAPI(title="AI Self-Healing Backend", version="0.1.0")

# In-cluster by default
k8s = KubernetesClient()
ai = AIProvider()

analyzer = LogAnalyzer(k8s=k8s, ai=ai)
remediator = Remediator(k8s=k8s, ai=ai)


class AnalyzeRequest(BaseModel):
    namespace: str = Field(..., description="Kubernetes namespace")
    workload: str = Field(..., description="Workload name (deployment/statefulset/pod) or pod")
    workload_kind: str = Field(
        "pod",
        description=(
            "Kind: pod|deployment|statefulset (used for targeted log scanning)"
        ),
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
    try:
        result = analyzer.analyze(
            namespace=req.namespace,
            workload=req.workload,
            workload_kind=req.workload_kind,
            tail_lines=req.tail_lines,
        )
        if req.auto_heal:
            # Strictly enforce guardrails before any K8s action.
            result["remediation"] = remediator.remediate(
                namespace=req.namespace,
                workload=req.workload,
                workload_kind=req.workload_kind,
                recommendation=result,
                dry_run=req.dry_run,
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))

