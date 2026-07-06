"""Developer dashboard API routes."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, HTTPException

from keprix.config.constants import DOCS_URL, PRODUCT_VERSION
from keprix.public_api.auth import require_developer_session
from keprix.public_api.keys import get_api_key_store
from keprix.public_api.logs import list_logs
from keprix.public_api.models_catalog import list_public_models
from keprix.public_api.rate_limits import PUBLIC_API_RULE
from keprix.public_api.schemas import CreateApiKeyRequest, WebhookCreateRequest
from keprix.public_api.tools_catalog import list_public_toolsets
from keprix.public_api.usage import usage_summary
from keprix.public_api.webhooks import get_webhook_store, sign_payload

router = APIRouter(prefix="/api/developer", tags=["developer"])


def _sdk_snippets(base_url: str = "http://localhost:3333") -> dict[str, str]:
    return {
        "python": (
            "from openai import OpenAI\n"
            f'client = OpenAI(api_key="kp_...", base_url="{base_url}/v1")\n'
            'print(client.chat.completions.create(model="keprix", messages=[{"role":"user","content":"hi"}]))'
        ),
        "typescript": (
            "import OpenAI from 'openai';\n"
            f"const client = new OpenAI({{ apiKey: process.env.KEPRIX_API_KEY, baseURL: '{base_url}/v1' }});\n"
            'const response = await client.chat.completions.create({ model: "keprix", messages: [{ role: "user", content: "hi" }] });'
        ),
        "curl": (
            f'curl -X POST {base_url}/v1/chat/completions \\\n'
            '  -H "Authorization: Bearer kp_..." \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -d \'{"model":"keprix","messages":[{"role":"user","content":"hello"}]}\''
        ),
    }


@router.get("/keys")
async def list_keys(_session: str = Depends(require_developer_session)) -> dict:
    keys = get_api_key_store().list_keys()
    return {"keys": [key.model_dump() for key in keys]}


@router.post("/keys")
async def create_key(
    body: CreateApiKeyRequest,
    _session: str = Depends(require_developer_session),
) -> dict:
    created = get_api_key_store().create(body)
    return created.model_dump()


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: str,
    _session: str = Depends(require_developer_session),
) -> dict:
    if not get_api_key_store().revoke(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"revoked": True, "id": key_id}


@router.get("/usage")
async def developer_usage(
    days: int = 30,
    workspace_id: str = "default",
    _session: str = Depends(require_developer_session),
) -> dict:
    return await usage_summary(workspace_id=workspace_id, days=days)


@router.get("/logs")
async def developer_logs(
    limit: int = 100,
    workspace_id: str | None = None,
    _session: str = Depends(require_developer_session),
) -> dict:
    return {"logs": list_logs(workspace_id=workspace_id, limit=limit)}


@router.get("/webhooks")
async def list_webhooks(_session: str = Depends(require_developer_session)) -> dict:
    hooks = get_webhook_store().list_webhooks()
    return {"webhooks": [hook.model_dump() for hook in hooks]}


@router.post("/webhooks")
async def create_webhook(
    body: WebhookCreateRequest,
    _session: str = Depends(require_developer_session),
) -> dict:
    record, secret = get_webhook_store().create(body)
    payload = record.model_dump()
    payload["signing_secret"] = secret
    payload["note"] = "Store the signing secret now; it will not be shown again."
    return payload


@router.post("/webhooks/test")
async def test_webhook(
    body: dict,
    _session: str = Depends(require_developer_session),
) -> dict:
    webhook_id = str(body.get("webhook_id", ""))
    secret = body.get("secret") or get_webhook_store().get_secret_for_test(webhook_id)
    if not secret:
        raise HTTPException(status_code=400, detail="Webhook secret required for test signing")
    payload = json.dumps({"event": "test", "timestamp": int(time.time())}).encode("utf-8")
    signature = sign_payload(secret, payload)
    return {
        "webhook_id": webhook_id,
        "signature": signature,
        "payload": payload.decode("utf-8"),
        "valid": True,
    }


@router.get("/dashboard")
async def developer_dashboard(_session: str = Depends(require_developer_session)) -> dict:
    keys = get_api_key_store().list_keys()
    hooks = get_webhook_store().list_webhooks()
    usage = await usage_summary()
    recent_errors = [
        log for log in list_logs(limit=20) if int(log.get("status_code", 200)) >= 400
    ]
    return {
        "version": PRODUCT_VERSION,
        "openapi_url": "/openapi.json",
        "docs_url": DOCS_URL,
        "api_keys": [key.model_dump() for key in keys],
        "webhooks": [hook.model_dump() for hook in hooks],
        "usage": usage,
        "rate_limits": {
            "agent_chat": f"{PUBLIC_API_RULE.limit} requests / {PUBLIC_API_RULE.window_seconds} seconds per API key",
            "general": "300 requests / 60 seconds",
        },
        "models": [model_id for model_id, _ in list_public_models()],
        "enabled_tools": list_public_toolsets(),
        "sdk": {
            "python": "sdk/python/README.md",
            "typescript": "sdk/typescript/README.md",
        },
        "sdk_snippets": _sdk_snippets(),
        "recent_errors": recent_errors,
    }
