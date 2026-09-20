"""Apply / diff capability presets using reversible plugin lifecycle (769)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from keprix.capability_presets.loader import get_preset, list_presets, load_preset_file
from keprix.capability_presets.schema import PresetValidationError
from keprix.capability_presets.state import get_active_state, save_active_state
from keprix.seams.bootstrap import ensure_default_seams
from keprix.seams.policy import PolicyWrappedFs, PolicyWrappedShell
from keprix.seams.providers import (
    LocalFsProvider,
    LocalShellProvider,
    SandboxedFsProvider,
    SandboxedShellProvider,
)
from keprix.seams.registry import get_seam_registry

logger = logging.getLogger(__name__)

PRESET_PLUGIN_PREFIX = "preset:"


def _preset_plugin_id(name: str) -> str:
    return f"{PRESET_PLUGIN_PREFIX}{name}"


def diff_presets(from_name: str | None, to_name: str) -> dict[str, Any]:
    target = get_preset(to_name)
    current = get_preset(from_name) if from_name else None
    cur_plugins = set((current or {}).get("plugins") or [])
    tgt_plugins = set(target.get("plugins") or [])
    cur_tools = {t["name"] for t in ((current or {}).get("declared_tools") or [])}
    tgt_tools = {t["name"] for t in (target.get("declared_tools") or [])}
    return {
        "from": from_name,
        "to": to_name,
        "plugins_add": sorted(tgt_plugins - cur_plugins),
        "plugins_remove": sorted(cur_plugins - tgt_plugins),
        "tools_add": sorted(tgt_tools - cur_tools),
        "tools_remove": sorted(cur_tools - tgt_tools),
        "seams_from": (current or {}).get("seams") or {},
        "seams_to": target.get("seams") or {},
        "soft_wall_to": target.get("soft_wall") or {},
    }


def _ensure_sandbox_providers(registry) -> Path:
    root = Path(tempfile.gettempdir()) / "keprix-preset-sandbox"
    root.mkdir(parents=True, exist_ok=True)
    if "policy:fs.sandboxed" not in set(registry.list_providers("fs")):
        registry.register("fs", PolicyWrappedFs(SandboxedFsProvider(root)))
    if "policy:shell.sandboxed" not in set(registry.list_providers("shell")):
        registry.register("shell", PolicyWrappedShell(SandboxedShellProvider(root)))
    if "policy:fs.local" not in set(registry.list_providers("fs")):
        registry.register("fs", PolicyWrappedFs(LocalFsProvider()), make_active=False)
    if "policy:shell.local" not in set(registry.list_providers("shell")):
        registry.register(
            "shell", PolicyWrappedShell(LocalShellProvider()), make_active=False
        )
    return root


def _activate_seam(seam: str, provider_id: str) -> str:
    ensure_default_seams()
    registry = get_seam_registry()
    _ensure_sandbox_providers(registry)
    available = registry.list_providers(seam)  # type: ignore[arg-type]
    if provider_id not in available:
        alt = (
            provider_id.replace("policy:", "", 1)
            if provider_id.startswith("policy:")
            else f"policy:{provider_id}"
        )
        if alt in available:
            provider_id = alt
        else:
            raise PresetValidationError(
                f"Unknown seam provider {provider_id!r} for {seam}; "
                f"available={available}"
            )
    registry.set_active(seam, provider_id)  # type: ignore[arg-type]
    return provider_id


def _mount_declared_tools_global(preset: dict[str, Any]) -> list[str]:
    from keprix.plugin_lifecycle import unmount_plugin
    from keprix_cli.plugins import (
        LoadedPlugin,
        PluginContext,
        PluginManifest,
        get_plugin_manager,
    )
    from tools.registry import registry as tool_registry

    plugin_id = _preset_plugin_id(preset["name"])
    unmount_plugin(plugin_id, who="preset")

    mgr = get_plugin_manager()
    if not mgr._discovered:
        mgr._discovered = True
    manifest = PluginManifest(
        name=plugin_id,
        key=plugin_id,
        source="user",
        kind="standalone",
    )
    mgr._plugins[plugin_id] = LoadedPlugin(manifest=manifest, enabled=True)
    ctx = PluginContext(manifest, mgr)

    mounted: list[str] = []
    for tool in preset.get("declared_tools") or []:
        name = tool["name"]

        def _handler(args, _name=name, **kwargs):
            return f'{{"ok": true, "preset_tool": "{_name}"}}'

        if tool_registry.get_entry(name) is not None:
            tool_registry.deregister(name)
        ctx.register_tool(
            name=name,
            toolset=f"preset_{preset['name']}",
            schema={
                "name": name,
                "description": tool.get("description") or name,
                "parameters": {"type": "object", "properties": {}},
            },
            handler=_handler,
            description=tool.get("description") or name,
        )
        mounted.append(name)
    return mounted


def _resolve_plugin_known(plugin_id: str) -> bool:
    try:
        from keprix_cli.plugins import get_plugin_manager

        mgr = get_plugin_manager()
        if not mgr._discovered:
            mgr.discover_and_load()
        if plugin_id in mgr._plugins:
            return True
        for key, loaded in mgr._plugins.items():
            if loaded.manifest.name == plugin_id or key.endswith("/" + plugin_id):
                return True
        return False
    except Exception:
        return False


def apply_preset(
    name: str,
    *,
    who: str = "operator",
    strict_plugins: bool | None = None,
) -> dict[str, Any]:
    """Apply a named capability pack. Reversible via 769 unmount on switch."""
    from keprix.plugin_lifecycle import disable_plugin_hot, enable_plugin_hot, unmount_plugin

    preset = get_preset(name)
    profile = (preset.get("soft_wall") or {}).get("profile")
    if profile in {"off", "disabled", "none", "bypass", "yolo"}:
        raise PresetValidationError("packs cannot disable Soft Wall")

    state = get_active_state()
    previous = state.get("active")
    delta = diff_presets(previous, preset["name"])

    unknown_mode = preset.get("unknown_plugins") or "fail"
    if strict_plugins is True:
        unknown_mode = "fail"
    elif strict_plugins is False:
        unknown_mode = "skip"

    if previous:
        unmount_plugin(_preset_plugin_id(str(previous)), who=who)
    for plugin_id in delta["plugins_remove"]:
        disable_plugin_hot(plugin_id, who=who)

    errors: list[str] = []
    mounted_plugins: list[str] = []
    for plugin_id in preset.get("plugins") or []:
        if not _resolve_plugin_known(plugin_id):
            msg = f"unknown plugin id: {plugin_id}"
            if unknown_mode == "fail":
                raise PresetValidationError(msg)
            errors.append(msg)
            continue
        result = enable_plugin_hot(plugin_id, who=who)
        if not result.get("ok"):
            msg = f"failed to mount plugin {plugin_id}: {result}"
            if unknown_mode == "fail":
                raise PresetValidationError(msg)
            errors.append(msg)
        else:
            mounted_plugins.append(plugin_id)

    for skill in preset.get("skills") or []:
        logger.info("preset %s requests skill %s (operator ensures installed)", name, skill)

    seam_active: dict[str, str] = {}
    for seam, provider_id in (preset.get("seams") or {}).items():
        seam_active[seam] = _activate_seam(seam, provider_id)

    declared = _mount_declared_tools_global(preset)

    new_state = {
        "active": preset["name"],
        "mounted_plugins": mounted_plugins,
        "declared_tools": declared,
        "seams": seam_active,
        "soft_wall": preset.get("soft_wall"),
        "previous": previous,
        "who": who,
    }
    save_active_state(new_state)

    return {
        "ok": True,
        "applied": preset["name"],
        "previous": previous,
        "diff": delta,
        "seams": seam_active,
        "declared_tools": declared,
        "mounted_plugins": mounted_plugins,
        "soft_wall": preset.get("soft_wall"),
        "errors": errors,
        "first_class_modules_untouched": [
            "playbooks",
            "billing",
            "document_vault",
            "channel_shield",
            "crm",
        ],
    }


def show_preset(name: str) -> dict[str, Any]:
    return get_preset(name)


def list_available_presets() -> list[dict[str, Any]]:
    return list_presets()


def apply_preset_file(path: str | Path, *, who: str = "operator") -> dict[str, Any]:
    """Validate a custom pack file, install under user packs dir, then apply."""
    import yaml

    from keprix.capability_presets.loader import user_packs_dir

    preset = load_preset_file(path)
    user = user_packs_dir()
    user.mkdir(parents=True, exist_ok=True)
    out = user / f"{preset['name']}.yaml"
    dump = {
        "name": preset["name"],
        "description": preset.get("description"),
        "version": preset.get("version", 1),
        "plugins": preset.get("plugins") or [],
        "skills": preset.get("skills") or [],
        "declared_tools": preset.get("declared_tools") or [],
        "seams": preset.get("seams") or {},
        "soft_wall": preset.get("soft_wall")
        or {"profile": "standard", "require_approval": True},
        "env_refs": preset.get("env_refs") or [],
        "unknown_plugins": preset.get("unknown_plugins") or "fail",
        "notes": preset.get("notes") or [],
    }
    out.write_text(yaml.safe_dump(dump, sort_keys=False), encoding="utf-8")
    return apply_preset(preset["name"], who=who)
