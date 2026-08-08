"""Manifest load, validate, diff, explain, redacted export (KUS-01)."""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from keprix.universal_sidecar.manifest.schema import (
    BLOCKED_HOST_SUFFIXES,
    BLOCKED_URI_SCHEMES,
    DANGEROUS_NODE_PREFIXES,
    EXECUTABLE_HOOK_KEYS,
    SAFE_BUILTIN_NODES,
    SECRET_FIELD_HINTS,
    manifest_json_schema,
)

try:
    import jsonschema
except ImportError:  # pragma: no cover - jsonschema is a runtime dep of keprix
    jsonschema = None  # type: ignore


@dataclass
class ValidationIssue:
    path: str
    reason: str
    example: str = ""
    migration: str = ""
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reason": self.reason,
            "example": self.example,
            "migration": self.migration,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    digest: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "digest": self.digest,
            "issues": [i.as_dict() for i in self.issues],
            "risk_flags": self.risk_flags,
            "project_key": self.manifest.get("project_key"),
        }


def _walk_for_secrets(obj: Any, path: str, issues: list[ValidationIssue]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = str(key).lower()
            child = f"{path}.{key}" if path else str(key)
            if key_l in EXECUTABLE_HOOK_KEYS:
                issues.append(
                    ValidationIssue(
                        path=child,
                        reason="executable hooks and inline code are prohibited",
                        example="declare a capability node from the installed catalog instead",
                        migration="remove hooks/import/exec fields; use installed nodes",
                    )
                )
            if any(h in key_l for h in SECRET_FIELD_HINTS) and isinstance(value, str):
                if not re.match(r"^(vault|env|secret):", value):
                    if len(value) > 8 and not value.startswith("$"):
                        issues.append(
                            ValidationIssue(
                                path=child,
                                reason="secret values are prohibited; use vault/env/secret references",
                                example="vault_ref: env:MY_PROJECT_TOKEN",
                                migration="replace literal with env: or vault: reference",
                            )
                        )
            _walk_for_secrets(value, child, issues)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _walk_for_secrets(item, f"{path}[{idx}]", issues)


def _validate_uri(uri: str, path: str, issues: list[ValidationIssue], *, allow_private: bool = False) -> None:
    try:
        parsed = urlparse(uri)
    except Exception:
        issues.append(ValidationIssue(path=path, reason="invalid URI", example="https://app.example.com"))
        return
    scheme = (parsed.scheme or "").lower()
    if scheme in BLOCKED_URI_SCHEMES or scheme not in {"http", "https"}:
        issues.append(
            ValidationIssue(
                path=path,
                reason=f"scheme '{scheme}' is not allowed",
                example="https://app.example.com/api",
            )
        )
        return
    if "@" in (parsed.netloc or ""):
        issues.append(
            ValidationIssue(
                path=path,
                reason="credentials in URI are prohibited",
                example="https://app.example.com (put secrets in vault_ref)",
            )
        )
    host = (parsed.hostname or "").lower()
    for suffix in BLOCKED_HOST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            issues.append(ValidationIssue(path=path, reason="metadata/link-local destinations blocked"))
    if ".." in (parsed.path or "") or "*" in uri:
        issues.append(
            ValidationIssue(
                path=path,
                reason="path traversal or unbounded wildcards are prohibited",
            )
        )
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    blocked = ip.is_loopback or ip.is_link_local or ip.is_private or str(ip).startswith("169.254.")
    if blocked and not allow_private:
        issues.append(
            ValidationIssue(
                path=path,
                reason="loopback/private/metadata addresses require egress.allow_* flags",
                migration="set egress.allow_loopback or egress.allow_private_networks explicitly",
            )
        )


def _semantic_capabilities(manifest: dict[str, Any], issues: list[ValidationIssue]) -> list[str]:
    risk_flags: list[str] = []
    installed = set(SAFE_BUILTIN_NODES)
    # Optionally include product pack nodes if registry available
    try:
        from keprix.product_sidecar.registry import get_product_pack_registry

        for pack in get_product_pack_registry().list_packs():
            full = get_product_pack_registry().get(pack["product_key"])
            if full:
                installed.update(full.nodes.keys())
    except Exception:
        pass

    for idx, cap in enumerate(manifest.get("capabilities") or []):
        node = str(cap.get("node") or "")
        path = f"capabilities[{idx}].node"
        if any(node.startswith(p) for p in DANGEROUS_NODE_PREFIXES):
            issues.append(
                ValidationIssue(
                    path=path,
                    reason=f"dangerous node '{node}' is disabled in universal quickstart",
                    migration="install a signed capability pack and sandbox profile, then grant explicitly",
                )
            )
            risk_flags.append(f"dangerous_node:{node}")
        elif node and node not in installed:
            issues.append(
                ValidationIssue(
                    path=path,
                    reason=f"unknown capability '{node}' is not in the installed catalog",
                    example="node: summarise",
                    migration="request only installed safe nodes or install the required pack",
                )
            )
    return risk_flags


def load_manifest(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return copy.deepcopy(source)
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def digest_manifest(manifest: dict[str, Any]) -> str:
    raw = json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_manifest(
    source: str | Path | dict[str, Any],
    *,
    check_vault_refs: bool = True,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    try:
        manifest = load_manifest(source)
    except Exception as exc:
        return ValidationResult(ok=False, issues=[ValidationIssue(path="$", reason=str(exc))])

    schema = manifest_json_schema()
    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in err.path) or "$"
            issues.append(
                ValidationIssue(
                    path=path,
                    reason=err.message,
                    example="see docs/universal-sidecar/manifest-reference.md",
                )
            )

    _walk_for_secrets(manifest, "", issues)

    egress = manifest.get("egress") or {}
    allow_private = bool(egress.get("allow_private_networks") or egress.get("allow_loopback"))
    if manifest.get("base_url"):
        _validate_uri(str(manifest["base_url"]), "base_url", issues, allow_private=allow_private)
    for idx, cb in enumerate(manifest.get("callback_urls") or []):
        _validate_uri(str(cb), f"callback_urls[{idx}]", issues, allow_private=allow_private)

    for idx, op in enumerate(manifest.get("connectors") or []):
        path = str(op.get("path") or "")
        if ".." in path or path.startswith("//") or "@" in path:
            issues.append(
                ValidationIssue(
                    path=f"connectors[{idx}].path",
                    reason="unsafe path template",
                    example="/api/orders/{id}",
                )
            )

    if check_vault_refs:
        auth = manifest.get("auth") or {}
        vault_ref = str(auth.get("vault_ref") or "")
        if vault_ref.startswith("env:"):
            env_name = vault_ref[4:]
            if env_name and env_name not in os.environ:
                issues.append(
                    ValidationIssue(
                        path="auth.vault_ref",
                        reason=f"environment reference '{env_name}' is not set (value not printed)",
                        severity="warning",
                        migration="export the env var or use vault: for production",
                    )
                )

    risk_flags = _semantic_capabilities(manifest, issues)
    errors = [i for i in issues if i.severity == "error"]
    return ValidationResult(
        ok=len(errors) == 0,
        issues=issues,
        digest=digest_manifest(manifest),
        manifest=manifest,
        risk_flags=risk_flags,
    )


def diff_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Highlight newly risky access; apply must be explicit for risk increases."""
    old_caps = {c.get("node") for c in (old.get("capabilities") or [])}
    new_caps = {c.get("node") for c in (new.get("capabilities") or [])}
    old_ops = {c.get("key") for c in (old.get("connectors") or [])}
    new_ops = {c.get("key") for c in (new.get("connectors") or [])}
    added_caps = sorted(new_caps - old_caps)
    added_ops = sorted(new_ops - old_ops)
    risky: list[str] = []
    for node in added_caps:
        if any(str(node).startswith(p) for p in DANGEROUS_NODE_PREFIXES):
            risky.append(f"capability:{node}")
    for op in (new.get("connectors") or []):
        if op.get("key") in added_ops and op.get("mode") in {"apply", "propose"}:
            risky.append(f"connector:{op.get('key')}:{op.get('mode')}")
    if (new.get("egress") or {}).get("allow_private_networks") and not (
        old.get("egress") or {}
    ).get("allow_private_networks"):
        risky.append("egress:allow_private_networks")
    return {
        "added_capabilities": added_caps,
        "removed_capabilities": sorted(old_caps - new_caps),
        "added_connectors": added_ops,
        "removed_connectors": sorted(old_ops - new_ops),
        "risky_changes": risky,
        "requires_explicit_apply": bool(risky),
        "old_digest": digest_manifest(old),
        "new_digest": digest_manifest(new),
    }


def explain_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_key": manifest.get("project_key"),
        "display_name": manifest.get("display_name"),
        "environment": manifest.get("environment"),
        "capability_count": len(manifest.get("capabilities") or []),
        "connector_count": len(manifest.get("connectors") or []),
        "event_count": len(manifest.get("events") or []),
        "memory_mode": (manifest.get("memory") or {}).get("mode", "ephemeral"),
        "approval_risks": (manifest.get("approvals") or {}).get("required_for_risk"),
        "digest": digest_manifest(manifest),
    }


def export_redacted(manifest: dict[str, Any]) -> dict[str, Any]:
    """Safe for support tickets: strip vault refs values to placeholders."""
    data = copy.deepcopy(manifest)

    def redact(obj: Any) -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                key_l = str(k).lower()
                if "vault_ref" in key_l or any(h in key_l for h in SECRET_FIELD_HINTS):
                    if isinstance(v, str) and re.match(r"^(vault|env|secret):", v):
                        kind, _, rest = v.partition(":")
                        out[k] = f"{kind}:<redacted:{len(rest)}>"
                    else:
                        out[k] = "<redacted>"
                else:
                    out[k] = redact(v)
            return out
        if isinstance(obj, list):
            return [redact(i) for i in obj]
        return obj

    redacted = redact(data)
    redacted["_redacted"] = True
    redacted["_digest"] = digest_manifest(manifest)
    return redacted


def plan_apply(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    validation = validate_manifest(new)
    diff = diff_manifests(old or {}, new) if old else {
        "added_capabilities": [c.get("node") for c in (new.get("capabilities") or [])],
        "risky_changes": [],
        "requires_explicit_apply": False,
        "new_digest": digest_manifest(new),
    }
    return {
        "validation": validation.as_dict(),
        "diff": diff,
        "can_apply": validation.ok,
        "requires_confirm": bool(diff.get("requires_explicit_apply")),
    }
