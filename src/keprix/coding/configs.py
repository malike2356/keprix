"""Coding agent configuration profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "default": {
        "allow_bash": True,
        "require_human_review": False,
        "use_filemap": True,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 20,
    },
    "bash_only": {
        "allow_bash": True,
        "require_human_review": False,
        "use_filemap": False,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 5,
    },
    "human_review": {
        "allow_bash": True,
        "require_human_review": True,
        "use_filemap": True,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 10,
    },
    "filemap_review": {
        "allow_bash": False,
        "require_human_review": True,
        "use_filemap": True,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 15,
    },
    "coding_challenge": {
        "allow_bash": True,
        "require_human_review": False,
        "use_filemap": True,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 30,
    },
    "locked_down": {
        "allow_bash": False,
        "require_human_review": True,
        "use_filemap": True,
        "allow_commit": False,
        "allow_push": False,
        "allow_destructive_git": False,
        "max_files_per_run": 3,
    },
}


@dataclass
class CodingProfile:
    name: str
    allow_bash: bool = True
    require_human_review: bool = False
    use_filemap: bool = True
    allow_commit: bool = False
    allow_push: bool = False
    allow_destructive_git: bool = False
    max_files_per_run: int = 20
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> CodingProfile:
        known = {key for key in DEFAULT_PROFILES["default"]}
        extra = {key: value for key, value in data.items() if key not in known}
        return cls(name=name, extra=extra, **{key: data.get(key, DEFAULT_PROFILES["default"][key]) for key in known})


def _load_profile_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        return {}


def load_profile(name: str) -> CodingProfile:
    base = dict(DEFAULT_PROFILES.get(name, DEFAULT_PROFILES["default"]))
    for suffix in (".yaml", ".yml", ".json"):
        path = _PROFILES_DIR / f"{name}{suffix}"
        if path.exists():
            data = _load_profile_file(path)
            if data:
                base.update(data)
            return CodingProfile.from_dict(name, base)
    if name not in DEFAULT_PROFILES:
        raise KeyError(f"Unknown coding profile: {name}")
    return CodingProfile.from_dict(name, base)


def list_profiles() -> list[str]:
    names = set(DEFAULT_PROFILES)
    if _PROFILES_DIR.exists():
        for path in _PROFILES_DIR.iterdir():
            if path.suffix in {".yaml", ".yml", ".json"}:
                names.add(path.stem)
    return sorted(names)
