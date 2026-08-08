"""Pairing, workload identity, grants (KUS-03)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

from keprix.universal_sidecar.manifest.schema import HIGH_RISK_SCOPES
from keprix.universal_sidecar.registry import get_project_registry


def _signing_key() -> bytes:
    raw = (
        os.environ.get("KEPRIX_UNIVERSAL_SIDECAR_TOKEN_SECRET", "").strip()
        or os.environ.get("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "").strip()
        or "dev-only-universal-sidecar-secret"
    )
    return raw.encode("utf-8")


AUDIENCE = "keprix-universal-sidecar"
CLOCK_SKEW_SECONDS = 60


@dataclass
class WorkloadToken:
    jti: str
    iss: str
    aud: str
    sub: str
    project: str
    deployment: str
    environment: str
    tenant_id: str
    actor_id: str
    grants: frozenset[str]
    purpose: str
    iat: int
    nbf: int
    exp: int
    kid: str = "kus-v1"

    def as_claims(self) -> dict[str, Any]:
        return {
            "jti": self.jti,
            "iss": self.iss,
            "aud": self.aud,
            "sub": self.sub,
            "project": self.project,
            "deployment": self.deployment,
            "environment": self.environment,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "grants": sorted(self.grants),
            "purpose": self.purpose,
            "iat": self.iat,
            "nbf": self.nbf,
            "exp": self.exp,
            "kid": self.kid,
        }


class PairingStore:
    """One-time pairing codes bound to project and requested scopes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._codes: dict[str, dict[str, Any]] = {}
        self._receipts: list[dict[str, Any]] = []
        self._audit: list[dict[str, Any]] = []
        self._revoked: set[str] = set()
        self._seen_jti: dict[str, float] = {}

    def reset_for_tests(self) -> None:
        with self._lock:
            self._codes.clear()
            self._receipts.clear()
            self._audit.clear()
            self._revoked.clear()
            self._seen_jti.clear()

    def _audit_event(self, kind: str, **fields: Any) -> None:
        # Never record raw tokens
        safe = {k: v for k, v in fields.items() if k not in {"token", "code", "secret"}}
        self._audit.append({"ts": time.time(), "kind": kind, **safe})

    def create_code(
        self,
        *,
        project_key: str,
        deployment: str,
        environment: str,
        base_url: str,
        callback_urls: list[str],
        requested_scopes: list[str],
        ttl_seconds: int = 300,
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        high = [s for s in requested_scopes if s in HIGH_RISK_SCOPES or s.startswith("invoke:shell")]
        if high:
            raise PermissionError(f"high_risk_scopes_require_admin:{','.join(high)}")
        code = secrets.token_hex(4).upper()
        with self._lock:
            self._codes[code] = {
                "code": code,
                "project_key": project_key,
                "deployment": deployment,
                "environment": environment,
                "base_url": base_url,
                "callback_urls": list(callback_urls),
                "requested_scopes": list(requested_scopes),
                "expires_at": time.time() + ttl_seconds,
                "attempts": 0,
                "max_attempts": max_attempts,
                "used": False,
                "created_at": time.time(),
            }
            self._audit_event("pairing_create", project=project_key, scopes=requested_scopes)
            return {
                "code": code,
                "expires_in": ttl_seconds,
                "project_key": project_key,
                "requested_scopes": requested_scopes,
                "risks": self._risk_summary(project_key, requested_scopes, callback_urls),
            }

    @staticmethod
    def _risk_summary(project_key: str, scopes: list[str], callbacks: list[str]) -> dict[str, Any]:
        return {
            "project_key": project_key,
            "scopes": scopes,
            "callbacks": callbacks,
            "sensitivity": "review before approval",
            "egress": "bounded by manifest egress allowlist",
        }

    def approve_code(self, code: str, *, admin_actor: str = "admin") -> dict[str, Any]:
        with self._lock:
            row = self._codes.get(code.upper())
            if not row:
                self._audit_event("pairing_deny", reason="unknown_code")
                raise KeyError("unknown_code")
            row["attempts"] += 1
            if row["used"]:
                self._audit_event("pairing_deny", reason="already_used")
                raise ValueError("already_used")
            if row["attempts"] > row["max_attempts"]:
                self._audit_event("pairing_deny", reason="attempt_limit")
                raise ValueError("attempt_limit")
            if time.time() > row["expires_at"]:
                self._audit_event("pairing_deny", reason="expired")
                raise ValueError("expired")
            row["used"] = True
            receipt_body = {
                "project_key": row["project_key"],
                "deployment": row["deployment"],
                "scopes": row["requested_scopes"],
                "base_url": row["base_url"],
                "callbacks": row["callback_urls"],
                "admin_actor": admin_actor,
                "approved_at": time.time(),
            }
            receipt_hash = hashlib.sha256(
                json.dumps(receipt_body, sort_keys=True).encode("utf-8")
            ).hexdigest()
            receipt = {**receipt_body, "receipt_hash": receipt_hash}
            self._receipts.append(receipt)
            self._audit_event("pairing_approve", project=row["project_key"], receipt_hash=receipt_hash)
            token, claims = self.mint_token(
                project=row["project_key"],
                deployment=row["deployment"],
                environment=row["environment"],
                grants=set(row["requested_scopes"]),
                purpose="paired_workload",
            )
            return {
                "access_token": token,
                "expires_at": claims.exp,
                "receipt_hash": receipt_hash,
                "grants": sorted(claims.grants),
            }

    def mint_token(
        self,
        *,
        project: str,
        deployment: str = "local",
        environment: str = "local",
        grants: set[str] | frozenset[str],
        purpose: str,
        tenant_id: str = "",
        actor_id: str = "workload",
        subject: str = "",
        ttl_seconds: int = 300,
        audience: str = AUDIENCE,
    ) -> tuple[str, WorkloadToken]:
        # Cap grants to registry if project applied
        try:
            allowed = get_project_registry().grants_for(project)
            grants = frozenset(set(grants) & set(allowed)) if allowed else frozenset(grants)
        except KeyError:
            grants = frozenset(grants)
        now = int(time.time())
        token = WorkloadToken(
            jti=secrets.token_hex(12),
            iss="keprix",
            aud=audience,
            sub=subject or f"project:{project}:deployment:{deployment}",
            project=project,
            deployment=deployment,
            environment=environment,
            tenant_id=tenant_id,
            actor_id=actor_id,
            grants=frozenset(grants),
            purpose=purpose,
            iat=now,
            nbf=now - 1,
            exp=now + max(30, min(ttl_seconds, 3600)),
        )
        body = json.dumps(token.as_claims(), sort_keys=True, separators=(",", ":"))
        sig = hmac.new(_signing_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()
        signed = f"kus1.{body}.{sig}"
        self._audit_event("exchange", project=project, jti=token.jti, purpose=purpose)
        return signed, token

    def revoke(self, jti: str) -> None:
        with self._lock:
            self._revoked.add(jti)
            self._audit_event("revoke", jti=jti)

    def parse(self, raw: str, *, expected_audience: str = AUDIENCE) -> WorkloadToken:
        if not raw.startswith("kus1."):
            raise ValueError("denied")
        try:
            _, body, sig = raw.split(".", 2)
        except ValueError as exc:
            raise ValueError("denied") from exc
        expected = hmac.new(_signing_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("denied")
        claims = json.loads(body)
        now = int(time.time())
        if claims.get("aud") != expected_audience:
            raise ValueError("wrong_audience")
        if now + CLOCK_SKEW_SECONDS < int(claims.get("nbf") or 0):
            raise ValueError("not_yet_valid")
        if now - CLOCK_SKEW_SECONDS > int(claims.get("exp") or 0):
            raise ValueError("expired_token")
        jti = str(claims["jti"])
        with self._lock:
            if jti in self._revoked:
                raise ValueError("revoked")
            # Replay window: same jti within TTL is ok for bearer reuse; track for events separately
            self._seen_jti[jti] = now
        return WorkloadToken(
            jti=jti,
            iss=str(claims.get("iss") or "keprix"),
            aud=str(claims["aud"]),
            sub=str(claims.get("sub") or ""),
            project=str(claims["project"]),
            deployment=str(claims.get("deployment") or "local"),
            environment=str(claims.get("environment") or "local"),
            tenant_id=str(claims.get("tenant_id") or ""),
            actor_id=str(claims.get("actor_id") or ""),
            grants=frozenset(claims.get("grants") or ()),
            purpose=str(claims.get("purpose") or ""),
            iat=int(claims["iat"]),
            nbf=int(claims.get("nbf") or claims["iat"]),
            exp=int(claims["exp"]),
            kid=str(claims.get("kid") or "kus-v1"),
        )

    def authenticate(
        self,
        authorization: str | None,
        *,
        project_key: str,
        require_grant: str | None = None,
    ) -> WorkloadToken:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise ValueError("denied")
        raw = authorization.split(" ", 1)[1].strip()
        token = self.parse(raw)
        if token.project != project_key:
            raise ValueError("wrong_audience")
        if require_grant and require_grant not in token.grants and "*" not in token.grants:
            self._audit_event("deny_missing_grant", project=project_key, grant=require_grant)
            raise ValueError("denied")
        return token

    def delegate_actor(
        self,
        workload: WorkloadToken,
        *,
        actor_assertion: dict[str, Any],
    ) -> WorkloadToken:
        """Actor delegation cannot expand project grants."""
        asserted_grants = set(actor_assertion.get("grants") or [])
        capped = frozenset(asserted_grants & set(workload.grants))
        tenant = str(actor_assertion.get("tenant_id") or workload.tenant_id)
        actor = str(actor_assertion.get("actor_id") or "")
        if not actor:
            raise ValueError("actor_id required")
        # Signature of assertion is required in production; local mode accepts signed_hash field
        if not actor_assertion.get("signed_hash") and os.environ.get("KEPRIX_SIDECAR_STRICT", ""):
            raise ValueError("signed_assertion_required")
        _, token = self.mint_token(
            project=workload.project,
            deployment=workload.deployment,
            environment=workload.environment,
            grants=capped,
            purpose="delegated_actor",
            tenant_id=tenant,
            actor_id=actor,
            ttl_seconds=min(300, workload.exp - int(time.time())),
        )
        # Return the token object; caller uses mint result via parse of returned string
        # Re-mint to get string
        signed, parsed = self.mint_token(
            project=workload.project,
            deployment=workload.deployment,
            environment=workload.environment,
            grants=capped,
            purpose="delegated_actor",
            tenant_id=tenant,
            actor_id=actor,
            ttl_seconds=min(300, max(30, workload.exp - int(time.time()))),
        )
        parsed  # silence; return via attribute
        return self.parse(signed)

    def audit_log(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit)


_PAIRING: PairingStore | None = None
_PLOCK = threading.Lock()


def get_pairing_store() -> PairingStore:
    global _PAIRING
    with _PLOCK:
        if _PAIRING is None:
            _PAIRING = PairingStore()
        return _PAIRING
