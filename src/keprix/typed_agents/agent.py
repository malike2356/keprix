"""Typed agent runtime."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from keprix.typed_agents.approval import request_approval
from keprix.typed_agents.dependencies import SupportDependencies
from keprix.typed_agents.dynamic_instructions import InstructionFn, build_instructions
from keprix.typed_agents.output_validation import validate_output
from keprix.typed_agents.retries import RetryPolicy, RetryState
from keprix.typed_agents.schemas import AgentRunContext, ValidationRepairMessage, export_type_schemas
from keprix.typed_agents.tool_validation import validate_tool_arguments, validate_tool_result

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(slots=True)
class TypedTool:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]
    output_model: type[BaseModel] | None = None
    approval_action: str | None = None


@dataclass
class AgentRunResult(Generic[OutputT]):
    output: OutputT
    trace_id: str
    instructions: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    repairs: list[ValidationRepairMessage] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output.model_dump(),
            "trace_id": self.trace_id,
            "instructions": self.instructions,
            "tool_calls": list(self.tool_calls),
            "repairs": [repair.model_dump() for repair in self.repairs],
            "approvals": list(self.approvals),
        }


class TypedAgent(Generic[DepsT, OutputT]):
    def __init__(
        self,
        *,
        name: str,
        output_type: type[OutputT],
        deps_type: type[BaseModel],
        instructions: str,
        tools: list[TypedTool] | None = None,
        dynamic_instructions: list[InstructionFn] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.name = name
        self.output_type = output_type
        self.deps_type = deps_type
        self.base_instructions = instructions
        self.tools = {tool.name: tool for tool in (tools or [])}
        self.dynamic_instructions = dynamic_instructions or []
        self.retry_policy = retry_policy or RetryPolicy()

    def export_schemas(self, context: AgentRunContext | None = None) -> dict[str, Any]:
        return export_type_schemas(
            agent_name=self.name,
            output_type=self.output_type,
            dependencies_type=self.deps_type,
            tools=list(self.tools.values()),
            context=context,
        )

    def prepare_instructions(self, deps: DepsT, context: AgentRunContext) -> str:
        return build_instructions(
            self.base_instructions,
            deps,
            context,
            dynamic=self.dynamic_instructions,
        )

    async def invoke_tool(
        self,
        tool_name: str,
        raw_args: dict[str, Any],
        deps: DepsT,
        *,
        context: AgentRunContext,
        auto_approve: bool = False,
        retry_state: RetryState | None = None,
    ) -> dict[str, Any]:
        state = retry_state or RetryState(policy=self.retry_policy)
        tool = self.tools.get(tool_name)
        if tool is None:
            repair = ValidationRepairMessage(
                kind="tool_arguments",
                message=f"Unknown tool '{tool_name}'.",
                errors=[{"loc": ["tool_name"], "msg": "unknown tool"}],
            )
            state.record_repair(repair)
            return {"ok": False, "repair": repair, "repairs": state.repairs}

        while True:
            validated_args, arg_repair = validate_tool_arguments(tool.name, tool.input_model, raw_args)
            if arg_repair is not None:
                state.record_repair(arg_repair)
                if not state.can_retry():
                    return {"ok": False, "repair": arg_repair, "repairs": state.repairs}
                continue

            approval_action = tool.approval_action or "tool_execution"
            approval = await request_approval(
                action=approval_action,
                summary=f"{tool.name}: {validated_args.model_dump()}",
                auto_approve=auto_approve,
            )
            if approval.get("required") and not approval.get("approved"):
                return {"ok": False, "approval": approval, "repairs": state.repairs}

            result = await _maybe_await(tool.handler, validated_args, deps, context)
            validated_result, result_repair = validate_tool_result(tool.name, tool.output_model, result)
            if result_repair is not None:
                state.record_repair(result_repair)
                if not state.can_retry():
                    return {"ok": False, "repair": result_repair, "repairs": state.repairs}
                continue

            payload = validated_result.model_dump() if isinstance(validated_result, BaseModel) else validated_result
            return {
                "ok": True,
                "result": payload,
                "approval": approval,
                "repairs": state.repairs,
                "trace_id": context.trace_id,
            }

    async def finalize_output(
        self,
        raw_output: Any,
        deps: DepsT,
        *,
        context: AgentRunContext,
        auto_approve: bool = False,
    ) -> AgentRunResult[OutputT]:
        state = RetryState(policy=self.retry_policy)
        approval = await request_approval(
            action="output_publication",
            summary=f"Publish output for agent {self.name}",
            auto_approve=auto_approve,
        )
        approvals = [approval]
        while True:
            output, repair = validate_output(self.output_type, raw_output)
            if repair is not None:
                state.record_repair(repair)
                if not state.can_retry():
                    raise ValueError(repair.to_prompt_block())
                continue
            assert output is not None
            return AgentRunResult(
                output=output,
                trace_id=context.trace_id,
                instructions=self.prepare_instructions(deps, context),
                repairs=state.repairs,
                approvals=approvals,
            )

    async def run(
        self,
        *,
        deps: DepsT,
        context: AgentRunContext,
        tool_calls: list[dict[str, Any]],
        raw_output: Any,
        auto_approve: bool = False,
    ) -> AgentRunResult[OutputT]:
        instructions = self.prepare_instructions(deps, context)
        executed: list[dict[str, Any]] = []
        repairs: list[ValidationRepairMessage] = []
        approvals: list[dict[str, Any]] = []
        for call in tool_calls:
            response = await self.invoke_tool(
                call["name"],
                call.get("arguments", {}),
                deps,
                context=context,
                auto_approve=auto_approve,
            )
            executed.append({"tool": call["name"], "response": response})
            repairs.extend(response.get("repairs", []))
            if response.get("approval"):
                approvals.append(response["approval"])
            if not response.get("ok"):
                repair = response.get("repair")
                message = repair.to_prompt_block() if isinstance(repair, ValidationRepairMessage) else "tool failed"
                raise ValueError(message)
        result = await self.finalize_output(raw_output, deps, context=context, auto_approve=auto_approve)
        result.instructions = instructions
        result.tool_calls = executed
        result.repairs.extend(repairs)
        result.approvals.extend(approvals)
        return result


async def _maybe_await(func: Callable[..., Any], *args: Any) -> Any:
    value = func(*args)
    if isinstance(value, Awaitable):
        return await value
    return value


class LookupTicketInput(BaseModel):
    ticket_id: str = Field(min_length=3)


class LookupTicketOutput(BaseModel):
    ticket_id: str
    status: str
    subject: str


class SupportAnswer(BaseModel):
    ticket_id: str
    resolution: str
    cited_policy: str


def create_support_agent() -> TypedAgent[SupportDependencies, SupportAnswer]:
    async def lookup_ticket(args: LookupTicketInput, deps: SupportDependencies, _context: AgentRunContext) -> LookupTicketOutput:
        return LookupTicketOutput(
            ticket_id=args.ticket_id,
            status="open",
            subject=f"{deps.support_tier} support ticket",
        )

    def support_dynamic(deps: SupportDependencies, _context: AgentRunContext) -> str:
        return f"Route tickets for queue '{deps.ticket_queue}'. Never include secret values in replies."

    return TypedAgent(
        name="support-agent",
        output_type=SupportAnswer,
        deps_type=SupportDependencies,
        instructions="You are a typed Keprix support agent. Validate tool calls and cite policy in final answers.",
        tools=[
            TypedTool(
                name="lookup_ticket",
                description="Fetch ticket metadata",
                input_model=LookupTicketInput,
                output_model=LookupTicketOutput,
                handler=lookup_ticket,
                approval_action="tool_execution",
            )
        ],
        dynamic_instructions=[support_dynamic],
    )
