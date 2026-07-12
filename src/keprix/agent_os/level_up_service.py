"""Level-up remediation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.agent_os.connections_service import ConnectionsService
from keprix.agent_os.level_up_store import LevelUpPlan, LevelUpStore
from keprix.agent_os.level_up_templates import actions_from_export
from keprix.agent_os.maturity_audit_service import MaturityAuditService
from keprix.workspace.template_presets import workspace_root


class LevelUpService:
    def __init__(self, store: LevelUpStore | None = None) -> None:
        self.store = store or LevelUpStore()

    def generate(self, *, audit_id: str, workspace_path: str | None = None) -> LevelUpPlan:
        export = MaturityAuditService().export_to_level_up(audit_id)
        actions = actions_from_export(export)
        plan = LevelUpPlan(
            source_audit_id=audit_id,
            workspace_id=export.get("workspace_id"),
            workspace_path=workspace_path,
            actions=actions,
            estimated_score_delta=min(25.0, sum(8 if action.leverage == "high" else 4 for action in actions[:5])),
        )
        return self.store.save(plan)

    def get(self, plan_id: str) -> LevelUpPlan | None:
        return self.store.get(plan_id)

    def complete_action(self, plan_id: str, action_id: str) -> LevelUpPlan:
        plan = self._require(plan_id)
        for action in plan.actions:
            if action.id == action_id:
                action.completed = True
                return self.store.save(plan)
        raise KeyError(action_id)

    def apply_safe_stubs(self, plan_id: str) -> dict[str, Any]:
        plan = self._require(plan_id)
        root = Path(plan.workspace_path).expanduser().resolve() if plan.workspace_path else workspace_root(plan.workspace_id or "personal-os")
        root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for action in plan.actions:
            if action.kind != "auto_stub" or action.completed:
                continue
            if action.dimension == "context":
                path = root / "context" / "priorities.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists() or not path.read_text(encoding="utf-8").strip():
                    path.write_text("# Priorities\n\n## Next 90 days\n\n- \n", encoding="utf-8")
                    written.append(str(path))
            if action.dimension == "connections":
                result = ConnectionsService().init_template(workspace_path=str(root))
                written.append(result["path"])
            action.completed = True
        self.store.save(plan)
        return {"plan": plan.to_dict(), "written": written}

    def re_audit(self, plan_id: str) -> dict[str, Any]:
        plan = self._require(plan_id)
        audit = MaturityAuditService().run(workspace_id=plan.workspace_id, workspace_path=plan.workspace_path)
        return {"audit": audit.to_dict()}

    def _require(self, plan_id: str) -> LevelUpPlan:
        plan = self.store.get(plan_id)
        if plan is None:
            raise KeyError(plan_id)
        return plan
