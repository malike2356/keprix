"""Live installer for generated tools and skills."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.namespace import validate_tool_imports
from keprix.agent.keprix.schemas import GeneratedToolRecord
from keprix.agent.keprix.tool_signer import sign_tool, verify_tool

logger = logging.getLogger(__name__)


class LiveInstaller:
    async def install(self, record: GeneratedToolRecord) -> bool:
        namespace_violations = validate_tool_imports(record.tool_code)
        if namespace_violations:
            logger.error("Namespace violations for %s: %s", record.tool_name, namespace_violations)
            return False

        config = get_mutation_config()
        tools_dir = Path(config.generated_tools_dir)
        skills_dir = Path(config.generated_skills_dir)
        tools_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        metadata = {"record_id": record.id, "description": record.description}
        signature = sign_tool(record.tool_name, record.tool_code, metadata)

        tool_path = tools_dir / f"{record.tool_name}.py"
        skill_path = skills_dir / f"{record.tool_name}.skill"
        sig_path = tools_dir / f"{record.tool_name}.sig"
        meta_path = tools_dir / f"{record.tool_name}.meta.json"
        try:
            tool_path.write_text(record.tool_code, encoding="utf-8")
            skill_path.write_text(record.skill_yaml, encoding="utf-8")
            sig_path.write_text(signature, encoding="utf-8")
            meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to write generated tool files: %s", exc)
            return False

        from keprix.agent.keprix.store import get_generated_tool_store

        get_generated_tool_store().update(record.id, signature=signature)

        try:
            from tools.registry import registry

            registry.reload_generated_tools(tools_dir)
        except Exception as exc:
            logger.error("Failed to hot-reload generated tools: %s", exc)
            return False

        try:
            from keprix.agent.keprix.skill_registry import reload_generated_skills

            reload_generated_skills(skills_dir)
        except Exception:
            pass
        return True

    def remove_from_filesystem(self, record: GeneratedToolRecord) -> bool:
        config = get_mutation_config()
        tool_path = Path(config.generated_tools_dir) / f"{record.tool_name}.py"
        skill_path = Path(config.generated_skills_dir) / f"{record.tool_name}.skill"
        sig_path = Path(config.generated_tools_dir) / f"{record.tool_name}.sig"
        meta_path = Path(config.generated_tools_dir) / f"{record.tool_name}.meta.json"
        removed = False
        for path in (tool_path, skill_path, sig_path, meta_path):
            if path.exists():
                path.unlink()
                removed = True
        try:
            from tools.registry import registry

            registry.reload_generated_tools(Path(config.generated_tools_dir))
        except Exception:
            pass
        return removed


def verify_installed_tool(tool_path: Path) -> bool:
    sig_path = tool_path.with_name(f"{tool_path.stem}.sig")
    meta_path = tool_path.with_name(f"{tool_path.stem}.meta.json")
    if not sig_path.exists():
        return False
    tool_code = tool_path.read_text(encoding="utf-8")
    metadata = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return verify_tool(tool_path.stem, tool_code, sig_path.read_text(encoding="utf-8").strip(), metadata)
