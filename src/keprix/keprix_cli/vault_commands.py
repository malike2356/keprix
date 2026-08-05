"""Vault CLI command handlers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from keprix.vault.pack_registry import list_vault_packs
from keprix.vault.vault_init_service import init_vault, render_vault_template
from keprix.vault.vault_validator import validate_vault


def _vault_doctor(path: str) -> dict:
    root = Path(path).expanduser().resolve()
    markdown = list(root.rglob("*.md")) if root.exists() else []
    validation = validate_vault(root)
    return {
        "vault": str(root),
        "status": "healthy" if validation.get("ok") else "warning",
        "file_count": len(markdown),
        "folder_count": sum(1 for item in root.rglob("*") if item.is_dir()) if root.exists() else 0,
        "validation": validation,
    }


def _migrate_workspace(from_path: str, to_path: str) -> dict:
    source = Path(from_path).expanduser().resolve()
    target = Path(to_path).expanduser().resolve() / "wiki" / "from-workspace"
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(source.rglob("*.md")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(destination.relative_to(Path(to_path).expanduser().resolve()).as_posix())
    return {"from": str(source), "to": str(Path(to_path).expanduser().resolve()), "files_migrated": len(copied), "files": copied}


def cmd_vault(args) -> int:
    if args.vault_command == "list-packs":
        print(json.dumps({"packs": [pack.to_dict() for pack in list_vault_packs()]}, indent=2))
        return 0
    if args.vault_command == "init":
        print(json.dumps(init_vault(pack=args.pack, path=args.path, overwrite=args.overwrite), indent=2))
        return 0
    if args.vault_command == "validate":
        result = validate_vault(args.path)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    if args.vault_command == "doctor":
        result = _vault_doctor(args.path)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "healthy" else 1
    if args.vault_command == "migrate-workspace":
        print(json.dumps(_migrate_workspace(args.from_path, args.to_path), indent=2))
        return 0
    if args.vault_command == "render-template":
        print(json.dumps(render_vault_template(vault_path=args.path, template=args.template, output=args.output), indent=2))
        return 0
    if args.vault_command == "audit":
        from keprix.security.credential_vault_audit import audit_credentials

        payload = audit_credentials(
            expiring_days=getattr(args, "expiring_days", None),
            rotation_due=bool(getattr(args, "rotation_due", False)),
        )
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2))
        else:
            print(f"Credential vault audit ok={payload.get('ok')} issues={payload.get('issue_count')}")
        return 0 if payload.get("ok") else 1
    if args.vault_command == "ensure-default":
        from keprix.vault.capture import ensure_default_vault

        config = ensure_default_vault()
        print(json.dumps({"ok": True, "config": config.to_dict()}, indent=2))
        return 0
    print(json.dumps({"error": "unknown vault command"}))
    return 2
