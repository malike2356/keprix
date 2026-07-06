"""Optional fast-model JSON completion for ambient classification."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


async def complete_json(prompt: str, *, model: str = "fast") -> dict[str, Any]:
    base_url = os.environ.get("KEPRIX_LLM_BASE_URL", os.environ.get("OPENAI_BASE_URL", "")).rstrip("/")
    api_key = os.environ.get("KEPRIX_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    if not base_url or not api_key:
        raise RuntimeError("LLM credentials not configured for ambient classification")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
    content = body["choices"][0]["message"]["content"]
    return json.loads(content)
