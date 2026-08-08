"""Token exchange, shared-token compat, grant validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

from keprix.product_sidecar.types import ErrorCode, RequestContext


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _signing_key() -> bytes:
    raw = (
        os.environ.get("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "").strip()
        or os.environ.get("CARINA_KEPRIX_SHARED_TOKEN", "").strip()
        or os.environ.get("KEPRIX_CARINA_SHARED_TOKEN", "").strip()
        or "dev-only-sidecar-secret"
    )
    return raw.encode("utf-8")


def shared_bootstrap_token() -> str:
    return (
        os.environ.get("CARINA_KEPRIX_SHARED_TOKEN", "").strip()
        or os.environ.get("KEPRIX_CARINA_SHARED_TOKEN", "").strip()
    )


@dataclass
class SidecarToken:
    jti: str
    product: str
    deployment: str
    workspace_id: str
    actor_id: str
    roles: tuple[str, ...]
    grants: frozenset[str]
    entitlements: frozenset[str]
    purpose: str
    session_id: str
    audience: str
    iat: int
    exp: int
    kid: str = "sidecar-v1"

    def as_claims(self) -> dict[str, Any]:
        return {
            "jti": self.jti,
            "product": self.product,
            "deployment": self.deployment,
            "workspace_id": self.workspace_id,
            "actor_id": self.actor_id,
            "roles": list(self.roles),
            "grants": sorted(self.grants),
            "entitlements": sorted(self.entitlements),
            "purpose": self.purpose,
            "session_id": self.session_id,
            "aud": self.audience,
            "iat": self.iat,
            "exp": self.exp,
            "kid": self.kid,
        }


class TokenService:
    """HMAC short-lived tokens + bootstrap shared-token compat."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._revoked: set[str] = set()
        self._seen_jti: dict[str, float] = {}
        self._audit: list[dict[str, Any]] = []

    def reset_for_tests(self) -> None:
        with self._lock:
            self._revoked.clear()
            self._seen_jti.clear()
            self._audit.clear()

    def _sign(self, body: str) -> str:
        return hmac.new(_signing_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()

    def mint(
        self,
        *,
        product: str,
        workspace_id: str,
        actor_id: str,
        grants: set[str] | frozenset[str],
        purpose: str,
        deployment: str = "local",
        roles: tuple[str, ...] = ("operator",),
        entitlements: set[str] | frozenset[str] | None = None,
        session_id: str = "",
        ttl_seconds: int = 300,
        audience: str = "keprix-product-sidecar",
    ) -> tuple[str, SidecarToken]:
        now = int(time.time())
        token = SidecarToken(
            jti=secrets.token_hex(12),
            product=product,
            deployment=deployment,
            workspace_id=workspace_id,
            actor_id=actor_id,
            roles=roles,
            grants=frozenset(grants),
            entitlements=frozenset(entitlements or set()),
            purpose=purpose,
            session_id=session_id,
            audience=audience,
            iat=now,
            exp=now + max(30, min(ttl_seconds, 3600)),
        )
        claims = token.as_claims()
        body = _b64url_encode(
            json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signed = f"ks1.{body}.{self._sign(body)}"
        self._audit_event("exchange", product=product, workspace_id=workspace_id, jti=token.jti)
        return signed, token

    def revoke(self, jti: str) -> None:
        with self._lock:
            self._revoked.add(jti)

    def parse(self, raw: str) -> SidecarToken:
        if not raw.startswith("ks1."):
            raise ValueError(ErrorCode.DENIED.value)
        try:
            _, body, sig = raw.split(".", 2)
        except ValueError as exc:
            raise ValueError(ErrorCode.DENIED.value) from exc
        if not hmac.compare_digest(sig, self._sign(body)):
            raise ValueError(ErrorCode.DENIED.value)
        try:
            claims = json.loads(_b64url_decode(body).decode("utf-8"))
        except Exception as exc:
            raise ValueError(ErrorCode.DENIED.value) from exc
        token = SidecarToken(
            jti=str(claims["jti"]),
            product=str(claims["product"]),
            deployment=str(claims.get("deployment") or "local"),
            workspace_id=str(claims["workspace_id"]),
            actor_id=str(claims["actor_id"]),
            roles=tuple(claims.get("roles") or ()),
            grants=frozenset(claims.get("grants") or ()),
            entitlements=frozenset(claims.get("entitlements") or ()),
            purpose=str(claims.get("purpose") or ""),
            session_id=str(claims.get("session_id") or ""),
            audience=str(claims.get("aud") or ""),
            iat=int(claims["iat"]),
            exp=int(claims["exp"]),
            kid=str(claims.get("kid") or "sidecar-v1"),
        )
        now = int(time.time())
        if token.exp < now:
            raise ValueError(ErrorCode.EXPIRED_TOKEN.value)
        if token.audience != "keprix-product-sidecar":
            raise ValueError(ErrorCode.WRONG_AUDIENCE.value)
        with self._lock:
            if token.jti in self._revoked:
                raise ValueError(ErrorCode.DENIED.value)
            # Replay window: same jti within active lifetime is allowed for reads,
            # but exchange replay of bootstrap is separate. Mark seen for audit.
            prev = self._seen_jti.get(token.jti)
            self._seen_jti[token.jti] = now
            if prev is not None and now - prev < 0:
                raise ValueError(ErrorCode.REPLAY.value)
        return token

    def authenticate_request(
        self,
        *,
        authorization: str,
        product: str,
        correlation_id: str,
        required_audience: str = "keprix-product-sidecar",
    ) -> RequestContext:
        auth = authorization.strip()
        if not auth.lower().startswith("bearer "):
            raise ValueError(ErrorCode.DENIED.value)
        token_raw = auth[7:].strip()
        bootstrap = shared_bootstrap_token()
        if bootstrap and hmac.compare_digest(token_raw, bootstrap):
            # Deprecated compat mode: broad grants for migration.
            self._audit_event("compat_shared_token", product=product, correlation_id=correlation_id)
            return RequestContext(
                product=product,
                deployment="compat",
                workspace_id="",  # filled by body
                actor_id="shared-compat",
                grants=frozenset({"*"}),
                purpose="compat_shared_token",
                correlation_id=correlation_id,
                token_mode="shared_compat",
                audience=required_audience,
            )
        parsed = self.parse(token_raw)
        if parsed.product not in {product, "carina"} and not (
            product == "aiva" and parsed.product in {"aiva", "carina"}
        ):
            raise ValueError(ErrorCode.DENIED.value)
        if parsed.audience != required_audience:
            raise ValueError(ErrorCode.WRONG_AUDIENCE.value)
        return RequestContext(
            product=product,
            deployment=parsed.deployment,
            workspace_id=parsed.workspace_id,
            actor_id=parsed.actor_id,
            grants=parsed.grants,
            purpose=parsed.purpose,
            correlation_id=correlation_id,
            session_id=parsed.session_id,
            roles=parsed.roles,
            entitlements=parsed.entitlements,
            token_mode="exchange",
            audience=parsed.audience,
        )

    def has_grant(self, ctx: RequestContext, required: tuple[str, ...]) -> bool:
        if "*" in ctx.grants:
            return True
        return any(g in ctx.grants for g in required)

    def _audit_event(self, action: str, **fields: Any) -> None:
        with self._lock:
            self._audit.append({"action": action, "at": time.time(), **fields})
            if len(self._audit) > 5000:
                self._audit = self._audit[-2500:]

    def audit_tail(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit[-limit:])


_TOKEN_SERVICE: TokenService | None = None
_TS_LOCK = threading.Lock()


def get_token_service() -> TokenService:
    global _TOKEN_SERVICE
    with _TS_LOCK:
        if _TOKEN_SERVICE is None:
            _TOKEN_SERVICE = TokenService()
        return _TOKEN_SERVICE


# Entitlement maps (Stripe price IDs stay in .access; we only map SKU labels)
AIVA_WORKER_GRANTS = frozenset(
    {
        "node:agent.run",
        "agent:run",
        "node:soft_wall.request",
        "node:soft_wall.status",
        "soft_wall:request",
        "soft_wall:read",
        "node:crm.search",
        "crm:read",
        "node:crm.propose",
        "crm:propose",
        "node:crm.enroll",
        "crm:enroll",
        "node:crm.pipeline.read",
        "node:crm.analytics.summary",
        "node:vical.booking.offer",
        "vical:write",
        "node:booking.status",
        "vical:read",
        "node:memory.get",
        "memory:read",
        "node:memory.put",
        "memory:write",
        "node:rag.search",
        "rag:read",
        "node:playbook.start",
        "playbook:run",
        "node:playbook.status",
        "playbook:read",
        "node:jobs.create",
        "jobs:write",
        "node:jobs.cancel",
        "node:channels.notify",
        "channels:notify",
        "node:data.datasets.list",
        "data:read",
        "node:discovery.jobs.create",
        "discovery:write",
        "node:outreach.outbox.enqueue",
        "outreach:write",
        "node:scout.hooks.emit",
        "scout:hook",
        "node:data.jobs.create",
        "data:write",
        "node:data.export",
        "data:export",
    }
)

CARINA_ADMIN_EXTRA = frozenset(
    {
        "node:ops.engine.probe",
        "ops:read",
        "node:agent.interrupt",
        "node:crm.enrich.licensed",
        "crm:enrich",
    }
)


def grants_for_product(product: str, *, admin: bool = False) -> frozenset[str]:
    base = set(AIVA_WORKER_GRANTS)
    if product == "carina" or admin:
        base |= set(CARINA_ADMIN_EXTRA)
        base |= {"*"} if admin else set()
    return frozenset(base)
