"""LLM execution bridge for agent-runtime manifests."""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from keprix.agent_apps.app_manifest import AgentAppManifest
from keprix.agent_apps.entitlements import load_agent_apps_config

KNOWN_PERMISSIONS = frozenset({"network", "email_read", "filesystem"})


class AgentAppEnvError(ValueError):
    """Required environment variables are missing."""


class AgentAppPermissionError(PermissionError):
    """Required permissions are not granted for this workspace."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(f"Missing required permissions: {joined}")


@dataclass
class AgentAppRunResult:
    output: str
    status: str = "ok"
    session_id: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output,
            "status": self.status,
            "session_id": self.session_id,
            "artifacts": self.artifacts,
        }


def resolve_env_value(key: str) -> str | None:
    value = os.environ.get(key)
    if value and str(value).strip():
        return str(value).strip()
    try:
        from keprix_cli.config import get_env_value

        resolved = get_env_value(key)
        if resolved and str(resolved).strip():
            return str(resolved).strip()
    except Exception:
        pass
    return None


def missing_required_env(manifest: AgentAppManifest) -> list[str]:
    missing: list[str] = []
    for key in manifest.required_env:
        if not resolve_env_value(key):
            missing.append(key)
    return missing


def _permission_defaults() -> dict[str, bool]:
    cfg = load_agent_apps_config()
    defaults = (cfg.get("permissions") or {}).get("defaults") or {}
    return {
        "network": bool(defaults.get("network", True)),
        "email_read": bool(defaults.get("email_read", False)),
        "filesystem": bool(defaults.get("filesystem", True)),
    }


def _email_tools_configured() -> bool:
    for key in (
        "KEPRIX_EMAIL_IMAP_HOST",
        "IMAP_HOST",
        "SMTP_HOST",
        "KEPRIX_EMAIL_ACCOUNT",
    ):
        if resolve_env_value(key):
            return True
    return False


def is_permission_granted(permission: str) -> bool:
    env_key = f"KEPRIX_AGENT_APP_GRANT_{permission.upper()}"
    override = os.environ.get(env_key)
    if override is not None:
        return override.lower() in ("1", "true", "yes", "on")
    if permission == "email_read" and _email_tools_configured():
        return True
    defaults = _permission_defaults()
    if permission in defaults:
        return bool(defaults[permission])
    return permission not in KNOWN_PERMISSIONS or True


def missing_required_permissions(manifest: AgentAppManifest) -> list[str]:
    return [perm for perm in manifest.required_permissions if not is_permission_granted(perm)]


def readiness_state(manifest: AgentAppManifest) -> dict[str, Any]:
    missing_env = missing_required_env(manifest)
    missing_permissions = missing_required_permissions(manifest)
    permission_links = [
        {
            "permission": perm,
            "href": "/settings",
            "message": _permission_message(perm),
        }
        for perm in missing_permissions
    ]
    return {
        "ready": not missing_env and not missing_permissions,
        "missing_env": missing_env,
        "missing_permissions": missing_permissions,
        "vault_links": [{"key": key, "href": f"/vault?highlight={key}"} for key in missing_env],
        "permission_links": permission_links,
    }


def _permission_message(permission: str) -> str:
    if permission == "email_read":
        return "Enable email access in Settings and grant email_read for agent apps."
    if permission == "network":
        return "Grant network access for this agent app in Settings."
    if permission == "filesystem":
        return "Grant filesystem access for this agent app in Settings."
    return f"Grant permission '{permission}' in Settings."


def assert_runtime_ready(manifest: AgentAppManifest) -> None:
    missing_env = missing_required_env(manifest)
    if missing_env:
        raise AgentAppEnvError(f"Missing required environment variables: {', '.join(missing_env)}")
    missing_permissions = missing_required_permissions(manifest)
    if missing_permissions:
        raise AgentAppPermissionError(missing_permissions)


def build_user_message(
    manifest: AgentAppManifest,
    *,
    input_text: str,
    context: dict[str, Any] | None = None,
) -> str:
    context = context or {}
    form = context.get("form") or context.get("inputs") or {}
    if not isinstance(form, dict):
        form = {}
    app_dir = manifest.app_dir
    template_path = app_dir / "prompt_template.md" if app_dir else None
    if template_path and template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        rendered = template
        for key, value in form.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        rendered = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", rendered).strip()
        if rendered:
            return rendered
    if form:
        lines = [f"{key}: {value}" for key, value in form.items() if str(value).strip()]
        if lines:
            return "\n".join(lines)
    return input_text


def build_system_prompt(app_dir: Path, manifest: AgentAppManifest) -> str:
    instructions = (app_dir / "instructions.md").read_text(encoding="utf-8")
    sections = [instructions.strip()]
    tool_lines: list[str] = []
    for rel_path in manifest.tools:
        path = app_dir / rel_path
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        name = str(data.get("name") or path.stem)
        description = str(data.get("description") or "").strip()
        tool_lines.append(f"- {name}: {description}" if description else f"- {name}")
    if tool_lines:
        sections.append("Declared app tools:\n" + "\n".join(tool_lines))
    playbook_lines: list[str] = []
    for rel_path in manifest.playbooks:
        path = app_dir / rel_path
        if path.exists():
            playbook_lines.append(f"- {path.name}")
    if playbook_lines:
        sections.append("Referenced playbooks:\n" + "\n".join(playbook_lines))
    return "\n\n".join(section for section in sections if section)


def resolve_allow_tools(manifest: AgentAppManifest) -> bool:
    if "network" in manifest.required_permissions:
        return is_permission_granted("network")
    if manifest.required_permissions:
        return any(is_permission_granted(perm) for perm in manifest.required_permissions)
    return True


async def run_agent_app_llm(
    app_dir: Path,
    manifest: AgentAppManifest,
    *,
    input_text: str = "",
    inputs: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    user_id: str | None = None,
    allow_tools: bool | None = None,
) -> AgentAppRunResult:
    del user_id  # reserved for per-user vault resolution in a later prompt
    assert_runtime_ready(manifest)
    merged_context = dict(context or {})
    if inputs:
        merged_context["form"] = inputs
    user_message = build_user_message(manifest, input_text=input_text, context=merged_context)
    if not user_message.strip():
        raise ValueError("Run input is empty")
    system_prompt = build_system_prompt(app_dir, manifest)
    if allow_tools is None:
        allow_tools = resolve_allow_tools(manifest)

    from keprix.public_api.agent_runtime import run_agent_chat_completion

    chat_result = await run_agent_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        allow_tools=allow_tools,
        session_id=f"agent-app:{manifest.name}",
    )
    if chat_result.failed:
        raise RuntimeError(chat_result.error or "Agent run failed")
    return AgentAppRunResult(
        output=chat_result.final_response,
        status="ok",
        session_id=chat_result.session_id,
    )


def run_agent_app_llm_sync(
    app_dir: Path,
    manifest: AgentAppManifest,
    *,
    input_text: str,
    context: dict[str, Any] | None = None,
    allow_tools: bool | None = None,
) -> dict[str, Any]:
    form = (context or {}).get("form") or (context or {}).get("inputs") or {}
    inputs = form if isinstance(form, dict) else {}

    async def _run() -> AgentAppRunResult:
        return await run_agent_app_llm(
            app_dir,
            manifest,
            input_text=input_text,
            inputs=inputs,
            context=context,
            allow_tools=allow_tools,
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        result = asyncio.run(_run())
    else:
        if loop.is_running():
            import concurrent.futures

            def _run_in_thread() -> AgentAppRunResult:
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    return new_loop.run_until_complete(_run())
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(_run_in_thread).result()
        else:
            result = loop.run_until_complete(_run())
    return result.to_dict()
