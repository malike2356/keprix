"""Stateful analytics code interpreter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from keprix.analytics.code_verifier import CodeVerifier, VerificationResult
from keprix.analytics.container_executor import ContainerExecutor, ExecutionResult
from keprix.analytics.dataframe_memory import DataFrameMemory
from keprix.analytics.plugin_runner import PluginRunner


@dataclass(slots=True)
class AnalyticsSession:
    session_id: str
    chat_history: list[dict[str, str]] = field(default_factory=list)
    code_history: list[str] = field(default_factory=list)
    variables_metadata: dict[str, str] = field(default_factory=dict)
    charts: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    dataframe_memory: DataFrameMemory = field(default_factory=DataFrameMemory)
    approved_network: bool = False
    approved_shell: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "chat_history": list(self.chat_history),
            "code_history": list(self.code_history),
            "variables_metadata": dict(self.variables_metadata),
            "dataframes": [schema.to_dict() for schema in self.dataframe_memory.list_schemas()],
            "charts": list(self.charts),
            "output_files": list(self.output_files),
            "artifacts": list(self.artifacts),
        }


class CodeInterpreter:
    def __init__(
        self,
        *,
        verifier: CodeVerifier | None = None,
        executor: ContainerExecutor | None = None,
        plugins: PluginRunner | None = None,
    ) -> None:
        self.verifier = verifier or CodeVerifier()
        self.executor = executor or ContainerExecutor(container_required=True)
        self.plugins = plugins or PluginRunner()
        self.sessions: dict[str, AnalyticsSession] = {}

    def create_session(self) -> AnalyticsSession:
        session = AnalyticsSession(session_id=str(uuid4()))
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> AnalyticsSession | None:
        return self.sessions.get(session_id)

    def run_code(self, session: AnalyticsSession, code: str, namespace: dict[str, Any] | None = None) -> tuple[VerificationResult, ExecutionResult]:
        verification = self.verifier.verify(
            code,
            network_approved=session.approved_network,
            shell_approved=session.approved_shell,
        )
        if not verification.allowed:
            return verification, ExecutionResult(ok=False, stderr="; ".join(verification.errors))

        runtime_namespace = {
            "plugin": self.plugins.run,
            "anomaly_detection": lambda values: self.plugins.run("anomaly_detection", values=values),
        }
        runtime_namespace.update(namespace or {})
        result = self.executor.run_python(code, runtime_namespace)
        session.code_history.append(code)
        session.variables_metadata = {
            key: type(value).__name__
            for key, value in result.variables.items()
            if not key.startswith("_")
        }
        if "result" in result.variables:
            session.artifacts.append({"type": "result", "value": result.variables["result"]})
        return verification, result


analytics_interpreter = CodeInterpreter()
