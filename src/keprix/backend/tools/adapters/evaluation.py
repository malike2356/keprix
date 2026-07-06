"""Evaluation adapters (Prompt 56)."""

from __future__ import annotations

from typing import Any

from keprix.backend.tools.adapters.base import AdapterResult, ToolAdapter


class EvaluationAdapter(ToolAdapter):
    category = "evaluation"
    risk_level = "low"
    supports_dry_run = True

    def __init__(self, *, name: str, env_key: str = "", setup_doc: str = "") -> None:
        self.name = name
        self.required_env = (env_key,) if env_key else ()
        self.setup_doc = setup_doc

    async def execute(self, action: str, params: dict[str, Any]) -> AdapterResult:
        if self.name == "keprix_eval":
            from keprix.evals.runner import get_runner

            suite = str(params.get("suite") or "chat_basics")
            try:
                summary = await get_runner().run_suite(suite)
            except KeyError:
                return AdapterResult(ok=False, error=f"Eval suite not found: {suite}")
            return AdapterResult(
                ok=True,
                data={
                    "suite": summary.suite,
                    "passed": summary.passed,
                    "total": summary.total,
                    "pass_rate": summary.pass_rate,
                },
            )
        return AdapterResult(ok=True, data={"score": 0.0, "notes": params.get("notes", "")})


EVALUATION_ADAPTERS: list[ToolAdapter] = [
    EvaluationAdapter(name="patronus_eval", env_key="PATRONUS_API_KEY", setup_doc="Configure Patronus eval API."),
    EvaluationAdapter(name="keprix_eval", setup_doc="Runs internal keprix eval suites."),
]
