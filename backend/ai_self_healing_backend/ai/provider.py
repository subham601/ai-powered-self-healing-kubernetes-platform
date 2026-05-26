from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class AIResponse:
    root_cause: str
    severity: str
    signals: list[str]
    recommendations: list[str]
    actions: list[dict]


class AIProvider:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "ollama")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

    async def analyze_text(self, text: str) -> AIResponse:
        # Minimal heuristic + optional LLM enrichment.
        signals: list[str] = []
        t = text.lower()
        if "crashloopbackoff" in t or "crash loop" in t:
            signals.append("CrashLoopBackOff")
        if "oomkilled" in t or "out of memory" in t:
            signals.append("OOMKilled")
        if "imagepullbackoff" in t:
            signals.append("ImagePullBackOff")
        if "failed to schedule" in t or "no nodes" in t:
            signals.append("FailedScheduling")

        severity = "low"
        if "OOMKilled" in signals or "CrashLoopBackOff" in signals:
            severity = "high"

        root_cause = "Likely failure signals detected in logs."
        recommendations = [
            "Inspect pod events and restart/backoff history.",
            "Verify image tags, node capacity, and resource requests/limits.",
        ]
        actions: list[dict] = []

        if self.provider == "ollama":
            prompt = (
                "You are an SRE assistant. Analyze Kubernetes logs and return JSON with keys: "
                "root_cause, severity (low|medium|high), signals[], "
                "recommendations[], actions[] (each action has type and parameters).\n\n"
                f"LOGS:\n{text[:12000]}"
            )
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
            }

            try:
                r = httpx.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=60,
                )
                r.raise_for_status()
                raw = r.json().get("response", "")
                if isinstance(raw, str) and raw.strip():
                    root_cause = f"AI analysis: {raw.strip()}"
            except Exception:
                # Keep heuristic answer on any AI failure.
                pass

        return AIResponse(
            root_cause=root_cause,
            severity=severity,
            signals=signals,
            recommendations=recommendations,
            actions=actions,
        )

