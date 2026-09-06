"""Policy-controlled OSINT public-footprint enrichment (prompt 05).

Folds holehe / maigret / theHarvester into the deep-research pipeline. Disabled
by default; requires explicit opt-in AND a lawful-use acknowledgement. Engines
are external binaries detected via shutil.which (never bundled or auto-installed).
Subprocess hygiene: no shell=True, hard timeout, no secrets, parsed JSON only.

Breach databases and recovery-email/phone scraping are banned; those fields are
stripped before any write. Presence with no resolvable URL is recorded as
presence only. OSINT enriches the row; it never authorizes outbound.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from keprix.crm.models import ProvenanceKind
from keprix.crm.store import CrmStore

OSINT_ENABLED_ENV = "KEPRIX_OSINT_ENABLED"
OSINT_ACK_FLAG = "osint_lawful_use_acknowledged"

# Banned result keys: breach data and account-recovery/private contact fields.
_STRIP_KEYS = {
    "recovery_email",
    "recovery_phone",
    "recoveryEmail",
    "recoveryPhone",
    "breaches",
    "breach",
    "password",
    "passwords",
}

ENGINE_TIMEOUT_S = 60


def _utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def osint_enabled() -> bool:
    return os.environ.get(OSINT_ENABLED_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _cache_key(engine: str, *args: str) -> str:
    raw = "|".join([engine, *[a.strip().lower() for a in args if a]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _strip_sensitive(data: Any) -> Any:
    """Recursively remove banned keys and non-string scalars we never persist."""
    if isinstance(data, dict):
        return {k: _strip_sensitive(v) for k, v in data.items() if k not in _STRIP_KEYS}
    if isinstance(data, list):
        return [_strip_sensitive(v) for v in data]
    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    return None


def engine_available(engine: str) -> bool:
    return shutil.which(engine) is not None


def _run_engine(
    engine: str, args: list[str], *, timeout_s: int = ENGINE_TIMEOUT_S
) -> dict[str, Any]:
    """Run an external OSINT binary safely. Returns parsed JSON or an error dict."""
    if not engine_available(engine):
        return {"error": "not_configured", "engine": engine}
    cmd = [engine, *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "engine": engine}
    except Exception as exc:  # noqa: BLE001
        return {"error": "exec_failed", "engine": engine, "detail": str(exc)}
    stdout = (proc.stdout or "").strip()
    if proc.returncode != 0 and not stdout:
        return {
            "error": "engine_error",
            "engine": engine,
            "returncode": proc.returncode,
            "detail": (proc.stderr or "")[:500],
        }
    if not stdout:
        return {"error": "empty_output", "engine": engine}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Some engines emit JSON per line; take the first valid object.
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {"error": "unparseable_output", "engine": engine}


def holehe_lookup(email: str) -> dict[str, Any]:
    raw = _run_engine("holehe", [email, "--only-used", "--no-color", "--json"])
    if "error" in raw:
        return raw
    # holehe JSON is typically {account_name: {exists, ...}}; keep {service: exists} only.
    presence: dict[str, bool] = {}
    if isinstance(raw, dict):
        for service, info in raw.items():
            if isinstance(info, dict) and info.get("exists") is True:
                presence[str(service)] = True
    return {"presence": _strip_sensitive(presence)}


def maigret_lookup(username: str) -> dict[str, Any]:
    raw = _run_engine("maigret", [username, "--json"])
    if "error" in raw:
        return raw
    profiles: list[dict[str, str]] = []
    items = (
        raw if isinstance(raw, list) else raw.get("results", []) if isinstance(raw, dict) else []
    )
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url_user") or item.get("url") or "")
        status = str(item.get("status") or "")
        if url and status.lower() in {"claimed", "exists", "found"}:
            profiles.append({"site": str(item.get("site") or ""), "url": url, "status": status})
    return {"profiles": _strip_sensitive(profiles)}


def theharvester_domain(domain: str) -> dict[str, Any]:
    # Only an owned/authorised business domain; explicit backend allowlist, not '-b all'.
    raw = _run_engine("theHarvester", ["-d", domain, "-b", "linkedin,google", "-f", "json"])
    if "error" in raw:
        return raw
    emails = raw.get("emails") if isinstance(raw, dict) else []
    people = raw.get("people") if isinstance(raw, dict) else []
    result = {
        "emails": _strip_sensitive(list(emails or [])[:20]),
        "people": _strip_sensitive(list(people or [])[:20]),
    }
    return result


def _acknowledged(store: CrmStore, workspace_id: str) -> bool:
    try:
        from keprix.crm.connections import workspace_flag_enabled

        return workspace_flag_enabled(store, workspace_id, OSINT_ACK_FLAG)
    except Exception:  # noqa: BLE001
        return False


def _cache_get(store: CrmStore, key: str) -> dict[str, Any] | None:
    row = store._conn.execute(
        "SELECT result_json FROM crm_osint_cache WHERE key = ?", (key,)
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])
    except json.JSONDecodeError:
        return None


def _cache_put(store: CrmStore, key: str, engine: str, result: dict[str, Any]) -> None:
    store._conn.execute(
        "INSERT OR REPLACE INTO crm_osint_cache (key, engine, result_json, fetched_at) VALUES (?, ?, ?, ?)",
        (key, engine, json.dumps(result), _utcnow()),
    )
    store._conn.commit()


def _email_presence(email: str) -> dict[str, Any]:
    return holehe_lookup(email)


def _username_profiles(username: str) -> dict[str, Any]:
    return maigret_lookup(username)


def _primary_email(lead: dict[str, Any]) -> str:
    for item in lead.get("emails") or []:
        addr = item.get("address") if isinstance(item, dict) else item
        if addr:
            return str(addr)
    return ""


def _username_candidates(lead: dict[str, Any]) -> list[str]:
    email = _primary_email(lead)
    local = email.split("@", 1)[0] if email and "@" in email else ""
    first = str(lead.get("first_name") or "").strip().lower()
    last = str(lead.get("last_name") or "").strip().lower()
    cands = []
    if local:
        cands.append(local)
    if first and last:
        cands.append(f"{first}{last}")
        cands.append(f"{first}.{last}")
    return [c for c in cands if c]


def _domain(lead: dict[str, Any]) -> str:
    email = _primary_email(lead)
    if email and "@" in email:
        domain = email.rsplit("@", 1)[1].lower()
        from keprix.crm.research_enrich import FREE_MAIL_DOMAINS

        if domain not in FREE_MAIL_DOMAINS:
            return domain
    return ""


async def osint_enrich_lead(
    store: CrmStore,
    workspace_id: str,
    lead_id: str,
    *,
    injected: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ws = store._require_workspace(workspace_id)
    lead = store.get_lead(ws, lead_id)
    if not lead:
        return {"ok": False, "error": "not_found"}

    if not osint_enabled():
        return {
            "ok": True,
            "status": "disabled",
            "reason": "OSINT enrichment is disabled by default",
        }
    if not _acknowledged(store, ws):
        return {"ok": True, "status": "blocked", "reason": "lawful-use acknowledgement required"}

    email = _primary_email(lead)
    if not email:
        return {"ok": True, "status": "none", "reason": "lead has no email"}

    findings: dict[str, Any] = {}
    provenance: list[dict[str, Any]] = []

    # holehe: email presence (cache-first, engine on miss)
    presence: dict[str, Any] | None = None
    key = _cache_key("holehe", email)
    if injected and isinstance(injected.get("holehe"), dict):
        presence = dict(injected["holehe"])
        _cache_put(store, key, "holehe", presence)
    else:
        presence = _cache_get(store, key)
        if presence is None:
            presence = _email_presence(email)
            if presence is not None and "error" not in presence:
                _cache_put(store, key, "holehe", presence)
    if presence is not None and "error" not in presence:
        if presence.get("presence"):
            findings["email_presence"] = presence["presence"]
            provenance.append({"engine": "holehe", "field": "social_profiles.email_presence"})

    # maigret: username profiles (cache-first, engine on miss)
    profiles: list[dict[str, str]] = []
    for username in _username_candidates(lead):
        result: dict[str, Any] | None
        key = _cache_key("maigret", username)
        if injected and isinstance(injected.get("maigret"), dict):
            result = dict(injected["maigret"])
            _cache_put(store, key, "maigret", result)
        else:
            result = _cache_get(store, key)
            if result is None:
                result = _username_profiles(username)
                if result is not None and "error" not in result:
                    _cache_put(store, key, "maigret", result)
        if result is None or "error" in result:
            continue
        for p in result.get("profiles") or []:
            if p not in profiles:
                profiles.append(p)
        break  # first successful username only
    if profiles:
        findings["profiles"] = profiles
        provenance.append({"engine": "maigret", "field": "social_profiles.profiles"})
        for p in profiles:
            if "linkedin" in p.get("url", "").lower() and not (lead.get("linkedin_url") or ""):
                store.update_lead(ws, lead_id, linkedin_url=p["url"])
                break

    # theHarvester: business domain only (cache-first, engine on miss)
    domain = _domain(lead)
    if domain:
        result: dict[str, Any] | None
        key = _cache_key("theharvester", domain)
        if injected and isinstance(injected.get("theharvester"), dict):
            result = dict(injected["theharvester"])
            _cache_put(store, key, "theharvester", result)
        else:
            result = _cache_get(store, key)
            if result is None:
                result = theharvester_domain(domain)
                if result is not None and "error" not in result:
                    _cache_put(store, key, "theharvester", result)
        if result is not None and "error" not in result:
            if result.get("emails") or result.get("people"):
                findings["domain"] = result
                provenance.append({"engine": "theharvester", "field": "social_profiles.domain"})

    # Persist findings + status, fill-empty-only
    if findings:
        current_socials = {}
        raw_socials = lead.get("social_profiles") or "{}"
        if isinstance(raw_socials, str):
            try:
                current_socials = json.loads(raw_socials)
            except json.JSONDecodeError:
                current_socials = {}
        elif isinstance(raw_socials, dict):
            current_socials = dict(raw_socials)
        for k, v in findings.items():
            if k not in current_socials:
                current_socials[k] = v
        store.update_lead(
            ws, lead_id, social_profiles=json.dumps(current_socials), osint_status="done"
        )
    else:
        store.update_lead(ws, lead_id, osint_status="none")

    for prov in provenance:
        store.record_provenance(
            ws,
            entity_type="lead",
            entity_id=lead_id,
            field_name=prov["field"],
            value=findings,
            kind=ProvenanceKind.OBSERVED,
            adapter=f"osint:{prov['engine']}",
            verification_state="unverified",
        )

    # Auto-rescore after enrichment (prompt 09).
    try:
        from keprix.crm.ab_attribution import rescore_after_enrichment

        rescore_after_enrichment(store, ws, lead_id, reason="osint_enrich")
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "status": "done" if findings else "none",
        "findings": findings,
        "engines": [p["engine"] for p in provenance],
    }


def osint_enrich_lead_sync(store: CrmStore, workspace_id: str, lead_id: str) -> dict[str, Any]:
    return asyncio.run(osint_enrich_lead(store, workspace_id, lead_id))
