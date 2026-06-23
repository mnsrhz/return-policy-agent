from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def call_responses_json(client, *, model: str, prompt: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.0,
    )
    text = getattr(response, "output_text", "") or ""
    usage = _usage_to_dict(getattr(response, "usage", None))
    return parse_json_object(text), usage


def parse_json_object(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _usage_to_dict(usage: Optional[Any]) -> Dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {
        key: getattr(usage, key)
        for key in ("input_tokens", "output_tokens", "total_tokens")
        if hasattr(usage, key)
    }
