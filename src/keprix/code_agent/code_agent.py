"""Code-first agent that plans and acts through generated Python snippets."""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from typing import Any

from keprix.code_agent.action_syntax import CodePolicy, extract_code, validate_code
from keprix.code_agent.docker_provider import DockerSandboxProvider
from keprix.code_agent.e2b_provider import E2BSandboxProvider
from keprix.code_agent.modal_provider import ModalSandboxProvider
from keprix.code_agent.modality_inputs import ModalityBundle, normalize_inputs
from keprix.code_agent.sandbox_provider import SandboxProvider, SandboxResult
from keprix.code_agent.tool_collection import ToolCollection, merge_collections


@dataclass
class CodeAgentConfig:
    workspace_id: str = "default"
    provider: str = "docker"
    allowed_imports: set[str] = field(default_factory=lambda: {"json", "math", "statistics", "datetime", "collections"})
    allowed_paths: set[str] = field(default_factory=set)
    allow_network: bool = False
    max_runtime_s: int = 30
    memory_limit_mb: int = 256
    approval_threshold: str = "medium"
    output_schema: dict[str, Any] | None = None

    def to_policy(self) -> CodePolicy:
        return CodePolicy(
            allowed_imports=set(self.allowed_imports),
            allowed_paths=set(self.allowed_paths),
            allow_network=self.allow_network,
            max_runtime_s=self.max_runtime_s,
            memory_limit_mb=self.memory_limit_mb,
            approval_threshold=self.approval_threshold,
            output_schema=self.output_schema,
        )


@dataclass
class CodeAgentResult:
    ok: bool
    code: str
    stdout: str = ""
    stderr: str = ""
    result: Any = None
    needs_approval: bool = False
    errors: list[str] = field(default_factory=list)
    session_id: str = ""
    provider: str = ""


class CodeAgent:
    def __init__(
        self,
        config: CodeAgentConfig | None = None,
        *,
        provider: SandboxProvider | None = None,
        tools: ToolCollection | None = None,
    ) -> None:
        self.config = config or CodeAgentConfig()
        self.provider = provider or self._select_provider(self.config.provider)
        self.tools = tools or ToolCollection(name="empty")
        self._session = self.provider.start(self.config.workspace_id)

    @staticmethod
    def _select_provider(name: str) -> SandboxProvider:
        policy = CodePolicy()
        if name == "e2b":
            return E2BSandboxProvider()
        if name == "modal":
            return ModalSandboxProvider()
        if name == "docker":
            return DockerSandboxProvider(policy)
        if os.environ.get("KEPRIX_E2B_API_KEY"):
            return E2BSandboxProvider()
        if os.environ.get("KEPRIX_MODAL_TOKEN"):
            return ModalSandboxProvider()
        return DockerSandboxProvider(policy)

    def attach_tools(self, *collections: ToolCollection) -> None:
        self.tools = merge_collections(self.tools, *collections)

    def build_task_code(self, task: str, bundle: ModalityBundle | None = None) -> str:
        context = bundle.to_prompt_context() if bundle else task
        return textwrap.dedent(
            f"""
            import json
            import statistics

            data = [1, 2, 3, 4, 5]
            result = {{
                "task": {task!r},
                "context": {context!r},
                "mean": statistics.mean(data),
                "total": sum(data),
            }}
            print(json.dumps(result))
            """
        ).strip()

    def run_task(self, task: str, *, code: str | None = None, modalities: ModalityBundle | None = None) -> CodeAgentResult:
        bundle = modalities or normalize_inputs(text=task)
        snippet = code or self.build_task_code(task, bundle)
        parsed = extract_code(snippet)
        if not parsed.ok:
            return CodeAgentResult(ok=False, code=snippet, errors=parsed.errors)

        validated = validate_code(parsed.code, self.config.to_policy())
        if not validated.ok:
            return CodeAgentResult(ok=False, code=parsed.code, errors=validated.errors, needs_approval=self._needs_approval(validated.errors))

        sandbox_result = self.provider.run_code(self._session.session_id, validated.code)
        return self._from_sandbox(validated.code, sandbox_result)

    def run_generated_action(self, action_text: str) -> CodeAgentResult:
        parsed = extract_code(action_text)
        if not parsed.ok:
            return CodeAgentResult(ok=False, code="", errors=parsed.errors)
        validated = validate_code(parsed.code, self.config.to_policy())
        if not validated.ok:
            return CodeAgentResult(ok=False, code=parsed.code, errors=validated.errors, needs_approval=self._needs_approval(validated.errors))
        sandbox_result = self.provider.run_code(self._session.session_id, validated.code)
        return self._from_sandbox(validated.code, sandbox_result)

    def close(self) -> None:
        self.provider.stop(self._session.session_id)

    def _from_sandbox(self, code: str, sandbox_result: SandboxResult) -> CodeAgentResult:
        result = sandbox_result.data.get("result", sandbox_result.data.get("raw"))
        if result is None and sandbox_result.stdout:
            try:
                import json

                result = json.loads(sandbox_result.stdout.strip().splitlines()[-1])
            except Exception:
                result = sandbox_result.stdout.strip()
        return CodeAgentResult(
            ok=sandbox_result.ok,
            code=code,
            stdout=sandbox_result.stdout,
            stderr=sandbox_result.stderr,
            result=result,
            errors=[sandbox_result.error] if sandbox_result.error else [],
            session_id=self._session.session_id,
            provider=self.provider.name,
        )

    def _needs_approval(self, errors: list[str]) -> bool:
        if self.config.approval_threshold == "low":
            return False
        if self.config.approval_threshold == "high":
            return True
        return any("blocked" in error for error in errors)
