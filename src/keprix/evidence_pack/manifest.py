"""Evidence pack manifest building and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from keprix.config.constants import PRODUCT_VERSION
from keprix.governance.audit_events import get_audit_hmac_secret


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    *,
    pack_id: str,
    workspace_id: str,
    instance_id: str,
    date_from: str,
    date_to: str,
    events_sha256: dict[str, str],
    documents_sha256: dict[str, str],
    included_event_types: list[str],
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "pack_id": pack_id,
        "pack_version": "1.0",
        "generated_at": date_to,
        "workspace_id": workspace_id,
        "instance_id": instance_id,
        "keprix_version": PRODUCT_VERSION,
        "date_from": date_from,
        "date_to": date_to,
        "event_count": len(events_sha256),
        "document_count": len(documents_sha256),
        "included_event_types": sorted(included_event_types),
        "events_sha256": events_sha256,
        "documents_sha256": documents_sha256,
        "manifest_signature": "",
    }
    manifest["manifest_signature"] = sign_manifest(manifest)
    return manifest


def sign_manifest(manifest: dict[str, Any], *, secret: str | None = None) -> str:
    payload = {key: manifest[key] for key in sorted(manifest.keys()) if key != "manifest_signature"}
    key = (secret or get_audit_hmac_secret()).encode("utf-8")
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def verify_manifest_signature(manifest: dict[str, Any], *, secret: str | None = None) -> bool:
    provided = str(manifest.get("manifest_signature") or "")
    if not provided:
        return False
    expected = sign_manifest(manifest, secret=secret)
    return hmac.compare_digest(expected, provided)


def manifest_json_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")


VERIFY_TXT = """Evidence pack verification (Keprix)

1. For each file under events/, compute SHA-256 of the raw file bytes and compare to events_sha256 in manifest.json.
2. For each file under documents/, compare to documents_sha256 in manifest.json.
3. For each event JSON, verify the signature field using HMAC-SHA256 over canonical JSON (sorted keys, signature omitted).
4. Verify manifest_signature on manifest.json the same way (signature field excluded from HMAC input).
5. Obtain CLINICAL_EVENT_HMAC_SECRET from the operator who generated this pack.
"""
