"""Load and list capability presets (bundled YAML + optional user dir)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.capability_presets.schema import PresetValidationError, validate_preset

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def bundled_packs_dir() -> Path:
    return Path(__file__).resolve().parent / "packs"


def user_packs_dir() -> Path:
    try:
        from keprix_constants import get_keprix_home

        return Path(get_keprix_home()) / "capability_presets"
    except Exception:
        return Path.home() / ".keprix" / "capability_presets"


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise PresetValidationError("PyYAML is required to load capability presets")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return validate_preset(data, source=str(path))


def discover_preset_paths() -> list[Path]:
    paths: list[Path] = []
    bundled = bundled_packs_dir()
    if bundled.is_dir():
        paths.extend(sorted(bundled.glob("*.yaml")))
        paths.extend(sorted(bundled.glob("*.yml")))
    user = user_packs_dir()
    if user.is_dir():
        paths.extend(sorted(user.glob("*.yaml")))
        paths.extend(sorted(user.glob("*.yml")))
    return paths


def list_presets() -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for path in discover_preset_paths():
        try:
            preset = _load_yaml(path)
        except PresetValidationError:
            continue
        # Later paths (user) override bundled same name.
        seen[preset["name"]] = preset
    return [seen[k] for k in sorted(seen.keys())]


def get_preset(name: str) -> dict[str, Any]:
    key = name.strip()
    for preset in list_presets():
        if preset["name"] == key:
            return preset
    # Also try loading a direct path for custom packs under test.
    raise PresetValidationError(f"Unknown capability preset: {name!r}")


def load_preset_file(path: Path | str) -> dict[str, Any]:
    return _load_yaml(Path(path))
