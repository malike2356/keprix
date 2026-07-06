"""Agent app manifest loading and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

REQUIRED_FILES = ("agent.yaml", "instructions.md", "README.md")
OPTIONAL_DIRS = ("tools", "playbooks", "evals")
RUNTIME_TYPES = ("python", "agent", "hybrid")
INPUT_TYPES = ("text", "textarea", "select", "boolean", "number", "file")
OUTPUT_TYPES = ("markdown", "text", "json", "file")
CATEGORIES = ("productivity", "research", "finance", "custom")


@dataclass
class AgentAppInput:
    id: str
    label: str
    type: str = "text"
    required: bool = False
    default: Any = ""
    placeholder: str = ""
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "placeholder": self.placeholder,
            "options": self.options,
        }


@dataclass
class AgentAppOutput:
    id: str
    type: str = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type}


@dataclass
class AgentAppSchedule:
    suggested: str = ""
    timezone: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return {"suggested": self.suggested, "timezone": self.timezone}


@dataclass
class AgentAppBilling:
    tier: str = "free"
    meter: str = "runs_per_month"

    def to_dict(self) -> dict[str, Any]:
        return {"tier": self.tier, "meter": self.meter}


@dataclass
class AgentAppManifest:
    name: str
    version: str
    entrypoint: str
    display_name: str = ""
    description: str = ""
    category: str = "custom"
    icon: str | None = None
    runtime: Literal["python", "agent", "hybrid"] = "python"
    pre_entrypoint: str | None = None
    tools: list[str] = field(default_factory=list)
    playbooks: list[str] = field(default_factory=list)
    required_env: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    eval_suite: str | None = None
    inputs: list[AgentAppInput] = field(default_factory=list)
    outputs: list[AgentAppOutput] = field(default_factory=list)
    schedule: AgentAppSchedule | None = None
    billing: AgentAppBilling | None = None
    app_dir: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "runtime": self.runtime,
            "pre_entrypoint": self.pre_entrypoint,
            "tools": self.tools,
            "playbooks": self.playbooks,
            "required_env": self.required_env,
            "required_permissions": self.required_permissions,
            "eval_suite": self.eval_suite,
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "schedule": self.schedule.to_dict() if self.schedule else None,
            "billing": self.billing.to_dict() if self.billing else None,
            "app_dir": str(self.app_dir) if self.app_dir else None,
        }

    def summary_dict(self) -> dict[str, Any]:
        """Public API shape without filesystem paths."""
        data = self.to_dict()
        data.pop("app_dir", None)
        return data


class ManifestValidationError(ValueError):
    """Raised when an agent app folder fails validation."""


def _parse_inputs(raw_items: list[Any] | None) -> list[AgentAppInput]:
    inputs: list[AgentAppInput] = []
    seen: set[str] = set()
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        input_id = str(item.get("id") or "").strip()
        if not input_id:
            raise ManifestValidationError("Each input must have an id")
        if input_id in seen:
            raise ManifestValidationError(f"Duplicate input id: {input_id}")
        seen.add(input_id)
        input_type = str(item.get("type") or "text").strip()
        if input_type not in INPUT_TYPES:
            raise ManifestValidationError(f"Unsupported input type: {input_type}")
        options = [str(opt) for opt in item.get("options") or []]
        if input_type == "select" and not options:
            raise ManifestValidationError(f"Select input '{input_id}' requires options")
        inputs.append(
            AgentAppInput(
                id=input_id,
                label=str(item.get("label") or input_id).strip(),
                type=input_type,
                required=bool(item.get("required", False)),
                default=item.get("default", ""),
                placeholder=str(item.get("placeholder") or "").strip(),
                options=options,
            )
        )
    return inputs


def _parse_outputs(raw_items: list[Any] | None) -> list[AgentAppOutput]:
    outputs: list[AgentAppOutput] = []
    seen: set[str] = set()
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        output_id = str(item.get("id") or "").strip()
        if not output_id:
            raise ManifestValidationError("Each output must have an id")
        if output_id in seen:
            raise ManifestValidationError(f"Duplicate output id: {output_id}")
        seen.add(output_id)
        output_type = str(item.get("type") or "text").strip()
        if output_type not in OUTPUT_TYPES:
            raise ManifestValidationError(f"Unsupported output type: {output_type}")
        outputs.append(AgentAppOutput(id=output_id, type=output_type))
    return outputs


def load_manifest(app_dir: Path) -> AgentAppManifest:
    manifest_path = app_dir / "agent.yaml"
    if not manifest_path.exists():
        raise ManifestValidationError("Missing agent.yaml")
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    name = str(raw.get("name") or "").strip()
    runtime = str(raw.get("runtime") or "python").strip()
    if runtime not in RUNTIME_TYPES:
        raise ManifestValidationError(f"Unsupported runtime: {runtime}")
    category = str(raw.get("category") or "custom").strip()
    if category not in CATEGORIES:
        category = "custom"
    schedule_raw = raw.get("schedule")
    schedule = None
    if isinstance(schedule_raw, dict):
        schedule = AgentAppSchedule(
            suggested=str(schedule_raw.get("suggested") or "").strip(),
            timezone=str(schedule_raw.get("timezone") or "user").strip(),
        )
    billing_raw = raw.get("billing")
    billing = None
    if isinstance(billing_raw, dict):
        billing = AgentAppBilling(
            tier=str(billing_raw.get("tier") or "free").strip(),
            meter=str(billing_raw.get("meter") or "runs_per_month").strip(),
        )
    manifest = AgentAppManifest(
        name=name,
        version=str(raw.get("version") or "0.1.0").strip(),
        entrypoint=str(raw.get("entrypoint") or "").strip(),
        display_name=str(raw.get("display_name") or name).strip(),
        description=str(raw.get("description") or "").strip(),
        category=category,
        icon=str(raw["icon"]).strip() if raw.get("icon") else None,
        runtime=runtime,  # type: ignore[arg-type]
        pre_entrypoint=str(raw["pre_entrypoint"]).strip() if raw.get("pre_entrypoint") else None,
        tools=[str(item) for item in raw.get("tools") or []],
        playbooks=[str(item) for item in raw.get("playbooks") or []],
        required_env=[str(item) for item in raw.get("required_env") or []],
        required_permissions=[str(item) for item in raw.get("required_permissions") or []],
        eval_suite=str(raw["eval_suite"]).strip() if raw.get("eval_suite") else None,
        inputs=_parse_inputs(raw.get("inputs")),
        outputs=_parse_outputs(raw.get("outputs")),
        schedule=schedule,
        billing=billing,
        app_dir=app_dir.resolve(),
    )
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: AgentAppManifest) -> None:
    if not manifest.name:
        raise ManifestValidationError("Manifest name is required")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest.name):
        raise ManifestValidationError("Manifest name must be kebab-case")
    app_dir = manifest.app_dir
    if app_dir is None:
        raise ManifestValidationError("Manifest app_dir is required for validation")
    for filename in REQUIRED_FILES:
        if not (app_dir / filename).exists():
            raise ManifestValidationError(f"Missing required file: {filename}")
    if manifest.runtime in ("python", "hybrid"):
        if not manifest.entrypoint or ":" not in manifest.entrypoint:
            raise ManifestValidationError("Manifest entrypoint must be module:callable for python runtime")
        module_path = manifest.entrypoint.split(":", 1)[0].replace(".", "/") + ".py"
        if not (app_dir / module_path).exists():
            raise ManifestValidationError(f"Entrypoint module not found: {module_path}")
    if manifest.pre_entrypoint:
        if ":" not in manifest.pre_entrypoint:
            raise ManifestValidationError("pre_entrypoint must be module:callable")
        pre_module = manifest.pre_entrypoint.split(":", 1)[0].replace(".", "/") + ".py"
        if not (app_dir / pre_module).exists():
            raise ManifestValidationError(f"pre_entrypoint module not found: {pre_module}")
    for rel_path in manifest.tools + manifest.playbooks:
        if not (app_dir / rel_path).exists():
            raise ManifestValidationError(f"Referenced file not found: {rel_path}")
    if manifest.eval_suite and not (app_dir / manifest.eval_suite).exists():
        raise ManifestValidationError(f"Eval suite not found: {manifest.eval_suite}")
