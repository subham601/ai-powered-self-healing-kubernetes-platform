from __future__ import annotations

import json
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a single JSON object from model output."""
    if not text:
        return None

    text = text.strip()

    # If the whole thing is JSON
    try:
        v = json.loads(text)
        if isinstance(v, dict):
            return v
    except Exception:
        pass

    # Try to locate first { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        v = json.loads(candidate)
        if isinstance(v, dict):
            return v
    except Exception:
        return None

    return None


