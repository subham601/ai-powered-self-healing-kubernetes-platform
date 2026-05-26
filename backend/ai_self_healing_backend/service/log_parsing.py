from __future__ import annotations

import re


CRASHLOOP_PATTERNS = [
    re.compile(r"crashloopbackoff", re.IGNORECASE),
    re.compile(r"crash loop back off", re.IGNORECASE),
]

OOM_PATTERNS = [
    re.compile(r"oomkilled", re.IGNORECASE),
    re.compile(r"out of memory", re.IGNORECASE),
]

IMAGE_PULL_PATTERNS = [
    re.compile(r"imagepullbackoff", re.IGNORECASE),
    re.compile(r"manifest for .* not found", re.IGNORECASE),
    re.compile(r"failed to pull image", re.IGNORECASE),
]

FAILED_SCHEDULING_PATTERNS = [
    re.compile(r"failed to schedule", re.IGNORECASE),
    re.compile(r"no nodes available", re.IGNORECASE),
    re.compile(r"insufficient", re.IGNORECASE),
]


def extract_signals(logs: str) -> list[str]:
    signals: list[str] = []
    if any(p.search(logs) for p in CRASHLOOP_PATTERNS):
        signals.append("CrashLoopBackOff")
    if any(p.search(logs) for p in OOM_PATTERNS):
        signals.append("OOMKilled")
    if any(p.search(logs) for p in IMAGE_PULL_PATTERNS):
        signals.append("ImagePullBackOff")

    if any(
        p.search(logs) for p in FAILED_SCHEDULING_PATTERNS
    ):
        signals.append("FailedScheduling")
    return signals


def heuristic_confidence(signals: list[str]) -> str:
    # Deterministic fallback when AI JSON is missing/invalid.
    if "OOMKilled" in signals:
        return "high"
    if "CrashLoopBackOff" in signals:
        return "high"
    if "ImagePullBackOff" in signals:
        return "medium"
    if "FailedScheduling" in signals:
        return "medium"
    return "low"


def recommended_action_from_signals(signals: list[str]) -> tuple[str, dict]:
    # Conservative actions first.
    if "OOMKilled" in signals:
        return (
            "scale",
            {"reason": "OOMKilled detected; scale or adjust resources"},
        )

    if "CrashLoopBackOff" in signals:
        return "restart", {"reason": "CrashLoopBackOff detected"}
    if "ImagePullBackOff" in signals:
        return "noop", {"reason": "Image pull failed; requires image availability"}
    if "FailedScheduling" in signals:
        return (
            "noop",
            {
                "reason": (
                    "Scheduling failed; requires capacity/resource resolution"
                )
            },
        )
    return "noop", {"reason": "No known failure signature matched"}



