"""Initialize local vaults from starter packs."""

from __future__ import annotations

from datetime import date
import json
import shutil
from pathlib import Path
from typing import Any

from keprix.vault.pack_registry import get_vault_pack

MANIFEST_REL = Path(".keprix") / "vault-manifest.json"


def _copy_tree_missing(src: Path, dest: Path, *, overwrite: bool = False) -> list[str]:
    written: list[str] = []
    for item in sorted(src.rglob("*")):
        relative = item.relative_to(src)
        target = dest / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            continue
        shutil.copy2(item, target)
        written.append(str(relative))
    return written


def init_vault(*, pack: str, path: str, overwrite: bool = False) -> dict[str, Any]:
    vault_path = Path(path).expanduser().resolve()
    vault_path.mkdir(parents=True, exist_ok=True)
    pack_info = get_vault_pack(pack)
    pack_root = Path(pack_info.path) / "pack"
    if not pack_root.is_dir():
        raise FileNotFoundError(f"Vault pack files not found: {pack_root}")
    written = _copy_tree_missing(pack_root, vault_path, overwrite=overwrite)
    manifest_path = vault_path / MANIFEST_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for folder in (manifest.get("folders") or {}).values():
        (vault_path / str(folder)).mkdir(parents=True, exist_ok=True)
    manifest["installed_at"] = date.today().isoformat()
    manifest["pack_path"] = pack_info.path
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "pack": pack_info.to_dict(),
        "path": str(vault_path),
        "manifest_path": str(manifest_path),
        "written": written,
    }


def render_vault_template(*, vault_path: str, template: str, output: str | None = None, values: dict[str, str] | None = None) -> dict[str, Any]:
    root = Path(vault_path).expanduser().resolve()
    name = template.removesuffix(".md")
    template_path = root / "templates" / f"{name}.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {name}")
    data = {"date": date.today().isoformat(), **(values or {})}
    content = template_path.read_text(encoding="utf-8")
    for key, value in data.items():
        content = content.replace("{{" + key + "}}", value)
    if output:
        output_path = (root / output).resolve()
        output_path.relative_to(root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return {"content": content, "path": str(output_path)}
    return {"content": content}
