"""ML service tool registrations.

Prompt 229 registers the tool surface as not-ready stubs. Prompts 230-232
replace the handlers with concrete ML service calls while preserving names and
schemas for agents.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from keprix.tools.registry import registry

TOOLSET = "ml-service"


def _not_ready(capability: str) -> str:
    return json.dumps(
        {
            "status": "not_ready",
            "capability": capability,
            "message": f"{capability} is scaffolded and will be implemented by prompts 230-232.",
        }
    )


def _handler(capability: str):
    def _inner(_args: dict[str, Any], **_kwargs: Any) -> str:
        return _not_ready(capability)

    return _inner


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_url = os.environ.get("KEPRIX_ML_SERVICE_URL", "http://localhost:8200").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": f"ML service returned {exc.code}", "detail": detail}
    except OSError as exc:
        return {"error": "ML service unavailable", "detail": str(exc)}


def search_domain_knowledge_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    payload = {
        "query": args.get("query", ""),
        "pack_id": args.get("pack_id", ""),
        "top_k": args.get("top_k", 5),
        "score_threshold": args.get("score_threshold", 0.65),
    }
    data = _post_json("/embeddings/search", payload)
    if data.get("error"):
        return json.dumps({"found": False, **data})
    results = data.get("results") or []
    if not results:
        return json.dumps({"found": False, "message": "No relevant content found in this knowledge pack."})
    return json.dumps(
        {
            "found": True,
            "results": [
                {
                    "content": row.get("content"),
                    "score": row.get("score"),
                    "source": (row.get("metadata") or {}).get("source_label") or row.get("source_uri"),
                    "source_uri": row.get("source_uri"),
                    "chunk_index": row.get("chunk_index"),
                }
                for row in results
            ],
        }
    )


def detect_language_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(_post_json("/language/detect", {"text": args.get("text", "")}))


def translate_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/language/translate",
            {
                "text": args.get("text", ""),
                "src_lang": args.get("src_lang", "auto"),
                "tgt_lang": args.get("tgt_lang", "en"),
            },
        )
    )


def transcribe_audio_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/language/transcribe",
            {
                "audio_b64": args.get("audio_b64", ""),
                "mime_type": args.get("mime_type", "audio/ogg"),
                "language": args.get("language", "auto"),
            },
        )
    )


def synthesize_speech_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/language/synthesize",
            {
                "text": args.get("text", ""),
                "language": args.get("language", "en"),
                "voice_id": args.get("voice_id", ""),
            },
        )
    )


def classify_intent_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(_post_json("/classifiers/intent", {"text": args.get("text", ""), "context": args.get("context")}))


def classify_formation_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(_post_json("/classifiers/formation", {"description": args.get("description", "")}))


def predict_yield_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/classifiers/yield",
            {
                "formation": args.get("formation", "unknown"),
                "depth_m": args.get("depth_m", 0),
                "gps_lat": args.get("gps_lat"),
                "gps_lng": args.get("gps_lng"),
            },
        )
    )


def check_duplicate_member_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/classifiers/duplicate",
            {
                "first_name": args.get("first_name", ""),
                "last_name": args.get("last_name", ""),
                "phone": args.get("phone"),
                "dob": args.get("dob"),
                "existing_members": args.get("existing_members", []),
            },
        )
    )


def detect_agent_anomaly_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    return json.dumps(
        _post_json(
            "/classifiers/anomaly",
            {
                "agent_id": args.get("agent_id", ""),
                "action_sequence": args.get("action_sequence", []),
            },
        )
    )


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


registry.register(
    name="search_domain_knowledge",
    toolset=TOOLSET,
    schema=_schema(
        "search_domain_knowledge",
        "Search the keprix domain knowledge pack for relevant context.",
        {
            "query": {"type": "string"},
            "pack_id": {"type": "string"},
            "top_k": {"type": "number", "default": 5},
        },
        ["query", "pack_id"],
    ),
    handler=search_domain_knowledge_handler,
)

registry.register(
    name="detect_language",
    toolset=TOOLSET,
    schema=_schema(
        "detect_language",
        "Detect the language of a text string. Returns BCP-47 code.",
        {"text": {"type": "string"}},
        ["text"],
    ),
    handler=detect_language_handler,
)

registry.register(
    name="translate",
    toolset=TOOLSET,
    schema=_schema(
        "translate",
        "Translate text between languages. Pass src_lang='auto' to detect automatically.",
        {
            "text": {"type": "string"},
            "src_lang": {"type": "string", "default": "auto"},
            "tgt_lang": {"type": "string"},
        },
        ["text", "tgt_lang"],
    ),
    handler=translate_handler,
)

registry.register(
    name="transcribe_audio",
    toolset=TOOLSET,
    schema=_schema(
        "transcribe_audio",
        "Transcribe a voice message or audio clip to text.",
        {
            "audio_b64": {"type": "string"},
            "mime_type": {"type": "string"},
            "language": {"type": "string", "default": "auto"},
        },
        ["audio_b64", "mime_type"],
    ),
    handler=transcribe_audio_handler,
)

registry.register(
    name="synthesize_speech",
    toolset=TOOLSET,
    schema=_schema(
        "synthesize_speech",
        "Convert text to audio. Returns base64-encoded MP3.",
        {
            "text": {"type": "string"},
            "language": {"type": "string", "default": "en"},
            "voice_id": {"type": "string", "default": "default"},
        },
        ["text"],
    ),
    handler=synthesize_speech_handler,
)

registry.register(
    name="classify_intent",
    toolset=TOOLSET,
    schema=_schema(
        "classify_intent",
        "Classify the intent of an incoming message.",
        {"text": {"type": "string"}, "context": {"type": "string"}},
        ["text"],
    ),
    handler=classify_intent_handler,
)

registry.register(
    name="classify_formation",
    toolset=TOOLSET,
    schema=_schema(
        "classify_formation",
        "Classify geological formation type from a drilling log description.",
        {"description": {"type": "string"}},
        ["description"],
    ),
    handler=classify_formation_handler,
)

registry.register(
    name="predict_yield",
    toolset=TOOLSET,
    schema=_schema(
        "predict_yield",
        "Predict expected water yield range given formation data and location.",
        {
            "formation": {"type": "string"},
            "depth_m": {"type": "number"},
            "gps_lat": {"type": "number"},
            "gps_lng": {"type": "number"},
        },
        ["formation", "depth_m"],
    ),
    handler=predict_yield_handler,
)

registry.register(
    name="check_duplicate_member",
    toolset=TOOLSET,
    schema=_schema(
        "check_duplicate_member",
        "Check whether a new member registration is a likely duplicate.",
        {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "phone": {"type": "string"},
            "dob": {"type": "string"},
        },
        ["first_name", "last_name"],
    ),
    handler=check_duplicate_member_handler,
)

registry.register(
    name="detect_agent_anomaly",
    toolset=TOOLSET,
    schema=_schema(
        "detect_agent_anomaly",
        "Score whether an agent action sequence is anomalous for the playbook.",
        {
            "agent_id": {"type": "string"},
            "action_sequence": {"type": "array", "items": {"type": "string"}},
        },
        ["agent_id", "action_sequence"],
    ),
    handler=detect_agent_anomaly_handler,
)
