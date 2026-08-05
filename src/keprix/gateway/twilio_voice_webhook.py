"""Twilio inbound phone webhook with signature validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response

from keprix.voice.call_store import VoiceCallStore
from keprix.voice.caller_resolver import CallerResolver
from keprix.voice.personas.receptionist import receptionist_greeting
from keprix.voice.twiml_builder import connect_stream_response, reject_response


def validate_twilio_signature(url: str, params: dict[str, str], signature: str, auth_token: str) -> bool:
    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


@dataclass
class AivaWorker:
    id: str
    phone_number: str
    name: str = "Aiva"
    business_name: str = "the business"
    voice_id: str = "default"
    escalation_number: str | None = None


class InMemoryWorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, AivaWorker] = {}

    def register(self, worker: AivaWorker) -> None:
        self._workers[worker.phone_number] = worker

    async def get_by_phone(self, phone: str) -> AivaWorker | None:
        return self._workers.get(phone) or AivaWorker(id=phone or "default", phone_number=phone or "default")


class TwilioVoiceWebhook:
    def __init__(
        self,
        *,
        call_store: VoiceCallStore | None = None,
        caller_resolver: CallerResolver | None = None,
        worker_registry: InMemoryWorkerRegistry | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.call_store = call_store or VoiceCallStore()
        self.caller_resolver = caller_resolver or CallerResolver()
        self.worker_registry = worker_registry or InMemoryWorkerRegistry()
        self.auth_token = auth_token if auth_token is not None else os.getenv("TWILIO_AUTH_TOKEN", "")

    async def handle_inbound(self, request: Request) -> Response:
        form = await request.form()
        params = {key: str(value) for key, value in form.items()}
        if self.auth_token:
            signature = request.headers.get("X-Twilio-Signature", "")
            if not signature or not validate_twilio_signature(str(request.url), params, signature, self.auth_token):
                return Response(content=reject_response(), status_code=403, media_type="application/xml")

        called = params.get("To", "")
        worker = await self.worker_registry.get_by_phone(called)
        if worker is None:
            return Response(content=reject_response("busy"), media_type="application/xml")

        caller = params.get("From", "")
        call_sid = params.get("CallSid") or f"call-{caller}-{called}"
        resolved = await self.caller_resolver.resolve(caller)
        await self.call_store.create(
            call_sid,
            worker_id=worker.id,
            caller=caller,
            caller_name=resolved.name,
            caller_contact_id=resolved.contact_id,
        )

        base = str(request.base_url).rstrip("/")
        ws_base = base.replace("https://", "wss://").replace("http://", "ws://")
        greeting = receptionist_greeting(worker.business_name)
        xml = connect_stream_response(
            stream_url=f"{ws_base}/api/voice/stream/{call_sid}",
            greeting=greeting,
            call_sid=call_sid,
        )
        return Response(content=xml, media_type="application/xml")
