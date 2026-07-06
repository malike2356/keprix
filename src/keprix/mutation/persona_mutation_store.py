"""Workspace-specific persona field overrides (Prompt 152)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from keprix.mutation.prompt_store import PromptStore, get_prompt_store
from keprix.mutation.store import MutationRecord, MutationStore, get_mutation_store

logger = logging.getLogger(__name__)

_ALLOWED_FIELDS = frozenset({"system_prompt", "instructions", "name", "description"})


@dataclass
class PersonaMutation:
    persona_id: str
    workspace_id: str
    field: str
    before_value: str
    after_value: str


class PersonaMutationStore:
    def __init__(
        self,
        mutation_store: MutationStore | None = None,
        prompt_store: PromptStore | None = None,
    ) -> None:
        self._mutation_store = mutation_store or get_mutation_store()
        self._prompt_store = prompt_store or get_prompt_store()

    def get_overrides(self, workspace_id: str, persona_id: str) -> dict[str, str]:
        overrides: dict[str, str] = {}
        records, _total = self._mutation_store.list_mutations(
            workspace_id,
            tier="persona",
            status="approved",
            page=1,
            per_page=200,
        )
        persona_key = persona_id.upper()
        for record in records:
            if record.name.upper() != persona_key:
                continue
            field = str(record.metadata.get("field", ""))
            if not field:
                continue
            value = record.after_value or str(record.metadata.get("value", ""))
            if value:
                overrides[field] = value
        return overrides

    def stage_override(
        self,
        workspace_id: str,
        persona_id: str,
        field: str,
        new_value: str,
        rationale: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> MutationRecord:
        if field not in _ALLOWED_FIELDS:
            raise ValueError(f"unsupported persona field: {field}")

        current = self.get_overrides(workspace_id, persona_id).get(field, "")
        status = "approved" if confidence >= auto_approve_threshold else "staged"
        record = self._mutation_store.save_mutation_event(
            workspace_id=workspace_id,
            tier="persona",
            trigger="persona_mutation",
            status=status,
            name=persona_id.upper(),
            description=rationale,
            before_value=current or None,
            after_value=new_value,
            approved_by="auto" if status == "approved" else None,
            quality_score=confidence,
            metadata={"field": field, "persona_id": persona_id.upper(), "rationale": rationale},
        )

        if field == "system_prompt":
            self._prompt_store.stage_improvement(
                workspace_id=workspace_id,
                prompt_key=persona_id.lower(),
                suggested_content=new_value,
                rationale=rationale,
                confidence=confidence,
                auto_approve_threshold=auto_approve_threshold,
            )
        return record

    def rollback_override(
        self,
        workspace_id: str,
        persona_id: str,
        field: str,
        rolled_back_by: str,
    ) -> MutationRecord | None:
        records, _total = self._mutation_store.list_mutations(
            workspace_id,
            tier="persona",
            status="approved",
            page=1,
            per_page=200,
        )
        persona_key = persona_id.upper()
        active = None
        for record in records:
            if record.name.upper() != persona_key:
                continue
            if record.metadata.get("field") != field:
                continue
            active = record
            break
        if active is None:
            return None

        self._mutation_store.update_mutation_status(active.id, "rolled_back")
        rollback_record = self._mutation_store.save_mutation_event(
            workspace_id=workspace_id,
            tier="persona",
            trigger="rollback",
            status="rolled_back",
            name=persona_key,
            description=f"Rolled back persona field {field}",
            before_value=active.after_value,
            after_value=active.before_value,
            approved_by=rolled_back_by,
            rollback_of=active.id,
            metadata={"field": field, "persona_id": persona_key},
        )

        if field == "system_prompt":
            self._prompt_store.rollback_to_previous(workspace_id, persona_id.lower(), rolled_back_by)
        return rollback_record

    def approve_override(self, mutation_id: str, approved_by: str) -> MutationRecord | None:
        record = self._mutation_store.get_generated_tool(mutation_id)
        if record is None or record.tier != "persona":
            return None
        updated = self._mutation_store.update_mutation_status(mutation_id, "approved", approved_by=approved_by)
        if updated is None:
            return None
        field = str(updated.metadata.get("field", ""))
        if field == "system_prompt":
            versions, _total = self._prompt_store.list_prompt_versions(
                updated.workspace_id,
                prompt_key=updated.name.lower(),
                page=1,
                per_page=20,
            )
            for version in versions:
                if not version.is_active:
                    self._prompt_store.activate_version(version.id, approved_by)
                    break
        return updated


_store: PersonaMutationStore | None = None


def get_persona_mutation_store() -> PersonaMutationStore:
    global _store
    if _store is None:
        _store = PersonaMutationStore()
    return _store


def merge_persona_dict(persona_dict: dict, workspace_id: str) -> dict:
    """Apply workspace persona overrides onto a static persona dict."""
    persona_id = str(persona_dict.get("name", ""))
    if not persona_id:
        return persona_dict
    try:
        overrides = get_persona_mutation_store().get_overrides(workspace_id, persona_id)
    except Exception as exc:
        logger.debug("persona override merge skipped: %s", exc)
        return persona_dict
    if not overrides:
        return persona_dict
    merged = dict(persona_dict)
    for field, value in overrides.items():
        merged[field] = value
    return merged
