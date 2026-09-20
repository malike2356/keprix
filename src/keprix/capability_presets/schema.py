"""Capability preset schema validation."""

from __future__ import annotations

from typing import Any

ALLOWED_SOFT_WALL_PROFILES = frozenset({"standard", "strict"})
FORBIDDEN_SOFT_WALL = frozenset({"off", "disabled", "none", "bypass", "yolo"})
SEAM_IDS = frozenset({"fs", "shell", "memory", "llm", "subagent", "web"})


class PresetValidationError(ValueError):
    """Raised when a capability pack fails closed."""


def validate_preset(data: Any, *, source: str = "<preset>") -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PresetValidationError(f"{source}: root must be a mapping")

    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        raise PresetValidationError(f"{source}: name is required")
    name = name.strip()

    description = str(data.get("description") or "").strip()
    version = data.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise PresetValidationError(f"{source}: version must be a positive int")

    plugins = data.get("plugins") or []
    if not isinstance(plugins, list) or any(not isinstance(p, str) or not p.strip() for p in plugins):
        raise PresetValidationError(f"{source}: plugins must be a list of non-empty strings")

    skills = data.get("skills") or []
    if not isinstance(skills, list) or any(not isinstance(s, str) or not s.strip() for s in skills):
        raise PresetValidationError(f"{source}: skills must be a list of non-empty strings")

    declared_tools = data.get("declared_tools") or []
    if not isinstance(declared_tools, list):
        raise PresetValidationError(f"{source}: declared_tools must be a list")
    normalized_tools: list[dict[str, str]] = []
    for item in declared_tools:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            raise PresetValidationError(
                f"{source}: each declared_tools entry needs a name"
            )
        normalized_tools.append(
            {
                "name": str(item["name"]).strip(),
                "description": str(item.get("description") or "").strip(),
            }
        )

    seams = data.get("seams") or {}
    if not isinstance(seams, dict):
        raise PresetValidationError(f"{source}: seams must be a mapping")
    for seam_id, provider_id in seams.items():
        if seam_id not in SEAM_IDS:
            raise PresetValidationError(f"{source}: unknown seam {seam_id!r}")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise PresetValidationError(
                f"{source}: seam {seam_id!r} provider must be a non-empty string"
            )

    soft_wall = data.get("soft_wall") or {}
    if not isinstance(soft_wall, dict):
        raise PresetValidationError(f"{source}: soft_wall must be a mapping")
    profile = str(soft_wall.get("profile") or "standard").strip().lower()
    if profile in FORBIDDEN_SOFT_WALL:
        raise PresetValidationError(
            f"{source}: soft_wall.profile={profile!r} is forbidden "
            "(packs cannot disable Soft Wall)"
        )
    if profile not in ALLOWED_SOFT_WALL_PROFILES:
        raise PresetValidationError(
            f"{source}: soft_wall.profile must be one of "
            f"{sorted(ALLOWED_SOFT_WALL_PROFILES)}"
        )
    require_approval = soft_wall.get("require_approval", True)
    if require_approval is False:
        raise PresetValidationError(
            f"{source}: soft_wall.require_approval cannot be false"
        )

    # Reject any attempt to smuggle secret values into the pack.
    env_overlays = data.get("env") or data.get("env_overlays") or {}
    if env_overlays:
        raise PresetValidationError(
            f"{source}: env/env_overlays values are forbidden; use env_refs "
            "(key names only)"
        )
    env_refs = data.get("env_refs") or []
    if not isinstance(env_refs, list) or any(
        not isinstance(k, str) or not k.strip() or "=" in k for k in env_refs
    ):
        raise PresetValidationError(
            f"{source}: env_refs must be a list of env key names (no values)"
        )

    unknown_plugins_mode = str(data.get("unknown_plugins") or "fail").strip().lower()
    if unknown_plugins_mode not in {"fail", "skip"}:
        raise PresetValidationError(
            f"{source}: unknown_plugins must be 'fail' or 'skip'"
        )

    return {
        "name": name,
        "description": description,
        "version": version,
        "plugins": [p.strip() for p in plugins],
        "skills": [s.strip() for s in skills],
        "declared_tools": normalized_tools,
        "seams": {k: str(v).strip() for k, v in seams.items()},
        "soft_wall": {
            "profile": profile,
            "require_approval": True,
        },
        "env_refs": [k.strip() for k in env_refs],
        "unknown_plugins": unknown_plugins_mode,
        "notes": list(data.get("notes") or [])
        if isinstance(data.get("notes"), list)
        else [],
        "source": source,
    }
