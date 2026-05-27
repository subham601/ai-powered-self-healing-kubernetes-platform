from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


STRUCTURED_PROMPT = """You are an SRE assistant analyzing Kubernetes workload logs.
Return ONLY valid JSON (no markdown) with this schema:
{
  "root_cause": "string",
  "confidence": "low|medium|high",
  "signals": ["string"],
  "fix": "string",
  "remediation": {
    "type": "restart|rollback|scale|noop",
    "parameters": {}
  }
}
Choose remediation conservatively. Use noop if uncertain."""


@dataclass
class AIResponse:
    root_cause: str
    severity: str
    signals: list[str]
    recommendations: list[str]
    actions: list[dict]


class AIProvider:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "ollama").lower()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def analyze_text(self, text: str) -> AIResponse:
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

        raw_llm = await self._call_llm(text)
        if raw_llm:
            root_cause = raw_llm

        return AIResponse(
            root_cause=root_cause,
            severity=severity,
            signals=signals,
            recommendations=recommendations,
            actions=actions,
        )

    async def _call_llm(self, text: str) -> str | None:
        prompt = f"{STRUCTURED_PROMPT}\n\nLOGS:\n{text[:12000]}"
        try:
            if self.provider == "openai" and self.openai_api_key:
                return await self._openai(prompt)
            return await self._ollama(prompt)
        except Exception:
            return None

    async def _ollama(self, prompt: str) -> str | None:
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
            )
            r.raise_for_status()
            raw = r.json().get("response", "")
            return raw.strip() if isinstance(raw, str) and raw.strip() else None

    async def _openai(self, prompt: str) -> str | None:
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": STRUCTURED_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                # Normalize to string for downstream JSON extractor.
                return content.strip()
            return None
