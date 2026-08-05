"""Extract resource references and action class from tool calls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from keprix.security.resource_scopes.registry import (
    ActionClass,
    ResourceKindSpec,
    ServiceResourceSpec,
    resolve_service_for_tool,
)


@dataclass
class ResourceRef:
    service: str
    kind: str
    resource_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "service": self.service,
            "kind": self.kind,
            "resource_id": self.resource_id,
        }


@dataclass
class ExtractionResult:
    service: str | None
    action: ActionClass
    refs: list[ResourceRef] = field(default_factory=list)
    indeterminate_kinds: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "action": self.action,
            "refs": [r.to_dict() for r in self.refs],
            "indeterminate_kinds": sorted(self.indeterminate_kinds),
        }


def _read_path(obj: Any, dotted: str) -> list[Any]:
    current: list[Any] = [obj]
    for part in dotted.split("."):
        next_items: list[Any] = []
        for item in current:
            if not isinstance(item, dict):
                continue
            value = item.get(part)
            if value is None:
                continue
            if isinstance(value, list):
                next_items.extend(value)
            else:
                next_items.append(value)
        current = next_items
    return [v for v in current if isinstance(v, (str, int, float))]


def _as_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_as_ids(item))
        return out
    if isinstance(value, dict):
        for key in ("id", "name", "path", "full_name", "repo"):
            if key in value:
                return _as_ids(value[key])
        return []
    text = str(value).strip()
    return [text] if text else []


def classify_action(tool_name: str, args: dict[str, Any] | None, spec: ServiceResourceSpec | None) -> ActionClass:
    name = (tool_name or "").lower()
    blob = f"{name} {args or {}}".lower()
    if any(h in blob for h in ("delete", "remove", "drop", "destroy")):
        return "delete"
    if any(h in blob for h in ("deploy", "rollout", "kubectl_apply", "release")):
        return "deploy"
    if any(h in blob for h in ("mutate", "synthesize", "self_coding", "edit_repo")):
        return "mutate"
    hints = spec.write_hints if spec else ()
    if any(h in name for h in hints) or any(h in blob for h in hints):
        # Distinguish pure reads that contain "list" etc.
        if name.startswith("list_") or name.startswith("get_") or name.startswith("read_") or name.startswith("search_"):
            if not any(h in name for h in ("write", "create", "update", "delete", "send", "deploy", "edit")):
                return "read"
        return "write"
    if any(h in name for h in ("send", "post_message", "execute", "run_terminal", "bash")):
        return "side_effect"
    return "read"


def _kind_targeted(kind: ResourceKindSpec, args: dict[str, Any], tool_name: str) -> bool:
    blob = f"{tool_name} {args}".lower()
    return any(hint.lower() in blob for hint in kind.targets_kind_hints)


def extract_from_kind(
    service: str,
    kind: ResourceKindSpec,
    args: dict[str, Any],
    tool_name: str,
) -> tuple[list[ResourceRef], bool]:
    ids: list[str] = []
    for field_name in kind.arg_fields:
        if field_name in args:
            ids.extend(_as_ids(args.get(field_name)))
    for nested in kind.nested_fields:
        for value in _read_path(args, nested):
            ids.extend(_as_ids(value))
    blob = ""
    try:
        import json

        blob = json.dumps(args, default=str)
    except Exception:
        blob = str(args)
    for pattern in kind.arg_patterns:
        for match in re.finditer(pattern, blob, flags=re.IGNORECASE):
            if match.lastindex:
                ids.append(match.group(1))
            else:
                ids.append(match.group(0))
    cleaned = []
    seen: set[str] = set()
    for raw in ids:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    if cleaned:
        return (
            [ResourceRef(service=service, kind=kind.kind, resource_id=rid) for rid in cleaned],
            False,
        )
    if _kind_targeted(kind, args, tool_name):
        return [], True
    return [], False


def extract_resources(tool_name: str, args: dict[str, Any] | None = None) -> ExtractionResult:
    payload = args if isinstance(args, dict) else {}
    spec = resolve_service_for_tool(tool_name)
    action = classify_action(tool_name, payload, spec)
    if spec is None:
        return ExtractionResult(service=None, action=action)
    refs: list[ResourceRef] = []
    indeterminate: set[str] = set()
    for kind in spec.kinds:
        found, is_indeterminate = extract_from_kind(spec.service, kind, payload, tool_name)
        refs.extend(found)
        if is_indeterminate:
            indeterminate.add(kind.kind)
    return ExtractionResult(
        service=spec.service,
        action=action,
        refs=refs,
        indeterminate_kinds=indeterminate,
    )
