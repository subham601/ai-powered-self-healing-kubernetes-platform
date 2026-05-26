from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Confidence = Literal["low", "medium", "high"]
ActionType = Literal["restart", "rollback", "scale", "noop"]


class AIAction(BaseModel):
    type: ActionType = Field(..., description="Action type")
    parameters: dict[str, Any] = Field(default_factory=dict)


class AIAnalysis(BaseModel):
    root_cause: str = Field(..., description="Human readable root cause")
    confidence: Confidence = Field(..., description="Confidence level")
    signals: list[str] = Field(default_factory=list)
    fix: str = Field(..., description="Short recommended fix summary")

    remediation: AIAction = Field(
        ..., description="Single recommended remediation action (or noop)"
    )


class IncidentPacket(BaseModel):
    namespace: str
    workload: str
    workload_kind: str
    tail_lines: int

    analysis: AIAnalysis

    evidence: dict[str, Any] = Field(default_factory=dict)

