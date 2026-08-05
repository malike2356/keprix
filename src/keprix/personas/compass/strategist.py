"""Strategy formulation and framework facilitation for COMPASS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC, StrEnum
from typing import Any
from uuid import uuid4

from keprix.personas.compass.persona import COMPASS_PERSONA
from keprix.playbook.runtime.graph import END, PlaybookGraph
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.workspace.repository import workspace_repo

MIN_CLARIFYING_QUESTIONS = 3

DEFAULT_CLARIFYING_QUESTIONS = (
    "What outcome would make this strategy successful in the next 12 months?",
    "What constraints (budget, team capacity, timeline) are non-negotiable?",
    "Who is the primary customer or stakeholder affected by this decision?",
    "What has been tried already, and what were the results?",
    "What risks are you most concerned about if this goes wrong?",
)


class StrategyFramework(StrEnum):
    SWOT = "swot"
    PORTER = "porter"
    OKR = "okr"
    V2MOM = "v2mom"
    WARDLEY = "wardley"


@dataclass(slots=True)
class StrategyOption:
    name: str
    summary: str
    trade_offs: list[str]
    rejected_reason: str = ""
    score_estimate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "trade_offs": list(self.trade_offs),
            "rejected_reason": self.rejected_reason,
            "score_estimate": self.score_estimate,
        }


@dataclass
class StrategySession:
    session_id: str
    topic: str
    framework: str
    clarifying_questions: list[str] = field(default_factory=list)
    clarifying_answers: dict[str, str] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    framework_output: dict[str, Any] = field(default_factory=dict)
    options: list[StrategyOption] = field(default_factory=list)
    recommendation: str = ""
    trade_offs: list[str] = field(default_factory=list)
    quantified_estimates: dict[str, str] = field(default_factory=dict)
    document_id: str | None = None
    markdown: str = ""
    ready_for_recommendation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "framework": self.framework,
            "clarifying_questions": list(self.clarifying_questions),
            "clarifying_answers": dict(self.clarifying_answers),
            "assumptions": list(self.assumptions),
            "framework_output": self.framework_output,
            "options": [option.to_dict() for option in self.options],
            "recommendation": self.recommendation,
            "trade_offs": list(self.trade_offs),
            "quantified_estimates": dict(self.quantified_estimates),
            "document_id": self.document_id,
            "markdown": self.markdown,
            "ready_for_recommendation": self.ready_for_recommendation,
        }


def generate_clarifying_questions(topic: str, *, extra_context: str = "") -> list[str]:
    topic = topic.strip()
    questions = [
        f"What does success look like for '{topic}' in measurable terms?",
        DEFAULT_CLARIFYING_QUESTIONS[1],
        DEFAULT_CLARIFYING_QUESTIONS[2],
        DEFAULT_CLARIFYING_QUESTIONS[3],
        DEFAULT_CLARIFYING_QUESTIONS[4],
    ]
    if extra_context:
        questions.insert(1, f"Given this context ({extra_context[:120]}), what is the single biggest unknown?")
    return questions[: max(MIN_CLARIFYING_QUESTIONS, 5)]


def has_sufficient_clarification(answers: dict[str, str]) -> bool:
    answered = [value.strip() for value in answers.values() if value and value.strip()]
    return len(answered) >= MIN_CLARIFYING_QUESTIONS


def build_swot(topic: str, answers: dict[str, str]) -> dict[str, list[str]]:
    success = answers.get("success", answers.get("q0", "growth and retention"))
    constraints = answers.get("constraints", answers.get("q1", "limited budget"))
    return {
        "strengths": [
            f"Existing momentum around {topic}",
            "Clear stakeholder alignment on priorities",
        ],
        "weaknesses": [
            f"Constraint pressure: {constraints}",
            "Execution bandwidth may be limited",
        ],
        "opportunities": [
            f"Expand {topic} into adjacent segments",
            f"Target outcome: {success}",
        ],
        "threats": [
            "Competitors may move faster on similar plays",
            "Market conditions could shift demand",
        ],
    }


def build_porter_forces(topic: str) -> dict[str, str]:
    return {
        "rivalry": f"Moderate rivalry in {topic}; differentiation matters",
        "supplier_power": "Low to moderate; multiple vendor options",
        "buyer_power": "Moderate; buyers compare alternatives actively",
        "substitutes": "Indirect substitutes exist via manual workflows",
        "new_entrants": "Moderate barrier; distribution and trust are moats",
    }


def build_okrs(topic: str, answers: dict[str, str]) -> list[dict[str, Any]]:
    success = answers.get("success", answers.get("q0", "measurable growth"))
    return [
        {
            "objective": f"Establish leadership in {topic}",
            "key_results": [
                "Increase qualified pipeline by 25% in 2 quarters",
                f"Deliver on success metric: {success}",
                "Achieve NPS >= 40 among core users",
            ],
        }
    ]


def build_v2mom(topic: str) -> dict[str, str]:
    return {
        "vision": f"Become the trusted choice for {topic}",
        "values": "Clarity, evidence, customer outcomes",
        "methods": "Test small, measure, scale what works",
        "obstacles": "Resource constraints and market noise",
        "measures": "Revenue growth, retention, time-to-value",
    }


def build_wardley_map(topic: str) -> list[dict[str, str]]:
    return [
        {"component": f"{topic} core workflow", "evolution": "product", "visibility": "user-facing"},
        {"component": "Data integrations", "evolution": "custom-built", "visibility": "supporting"},
        {"component": "Hosting and auth", "evolution": "commodity", "visibility": "infrastructure"},
    ]


class CompassStrategist:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = COMPASS_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._canvas_template = self.persona.prompts_dir / "strategy_canvas.md"

    def start_session(
        self,
        topic: str,
        *,
        framework: str = StrategyFramework.SWOT,
        extra_context: str = "",
    ) -> StrategySession:
        questions = generate_clarifying_questions(topic, extra_context=extra_context)
        return StrategySession(
            session_id=str(uuid4()),
            topic=topic.strip(),
            framework=framework,
            clarifying_questions=questions,
            ready_for_recommendation=False,
        )

    def apply_framework(self, framework: str, topic: str, answers: dict[str, str]) -> dict[str, Any]:
        normalized = framework.lower()
        if normalized == StrategyFramework.PORTER:
            return {"porter_five_forces": build_porter_forces(topic)}
        if normalized == StrategyFramework.OKR:
            return {"okrs": build_okrs(topic, answers)}
        if normalized == StrategyFramework.V2MOM:
            return {"v2mom": build_v2mom(topic)}
        if normalized == StrategyFramework.WARDLEY:
            return {"wardley_map": build_wardley_map(topic)}
        return {"swot": build_swot(topic, answers)}

    def build_options(self, topic: str, framework_output: dict[str, Any]) -> list[StrategyOption]:
        focused = StrategyOption(
            name="Focused bet",
            summary=f"Double down on the highest-leverage segment for {topic}",
            trade_offs=["Slower expansion", "Higher concentration risk"],
            score_estimate=7.8,
        )
        diversified = StrategyOption(
            name="Diversified portfolio",
            summary="Pursue two adjacent bets with staged investment",
            trade_offs=["Higher coordination cost", "Slower single-segment dominance"],
            rejected_reason="Spreads resources before core motion is proven",
            score_estimate=6.4,
        )
        partner_led = StrategyOption(
            name="Partner-led GTM",
            summary="Accelerate via channel partners instead of direct sales",
            trade_offs=["Margin compression", "Less direct customer feedback"],
            rejected_reason="Partner pipeline not mature enough for primary motion",
            score_estimate=5.9,
        )
        _ = framework_output
        return [focused, diversified, partner_led]

    def formulate_recommendation(
        self,
        topic: str,
        *,
        framework: str,
        answers: dict[str, str],
        assumptions: list[str] | None = None,
    ) -> StrategySession:
        if not has_sufficient_clarification(answers):
            questions = generate_clarifying_questions(topic)
            return StrategySession(
                session_id=str(uuid4()),
                topic=topic,
                framework=framework,
                clarifying_questions=questions,
                clarifying_answers=answers,
                ready_for_recommendation=False,
            )

        framework_output = self.apply_framework(framework, topic, answers)
        options = self.build_options(topic, framework_output)
        primary = options[0]
        rejected = [option for option in options if option.rejected_reason]

        session = StrategySession(
            session_id=str(uuid4()),
            topic=topic,
            framework=framework,
            clarifying_questions=generate_clarifying_questions(topic),
            clarifying_answers=answers,
            assumptions=assumptions
            or [
                "Market demand remains stable over the next 2 quarters",
                "Team capacity can support one primary initiative",
                "Baseline conversion rates hold during execution",
            ],
            framework_output=framework_output,
            options=options,
            recommendation=(
                f"Pursue the '{primary.name}' path for {topic}: {primary.summary}. "
                "This balances impact and execution feasibility given current constraints."
            ),
            trade_offs=primary.trade_offs,
            quantified_estimates={
                "expected_revenue_lift_pct": "12-18%",
                "time_to_first_signal_weeks": "8-10",
                "investment_band_usd": "25000-60000",
            },
            ready_for_recommendation=True,
        )
        session.markdown = self.render_canvas(session, rejected_alternatives=rejected)
        return session

    def render_canvas(
        self,
        session: StrategySession,
        *,
        rejected_alternatives: list[StrategyOption] | None = None,
    ) -> str:
        template = self._canvas_template.read_text(encoding="utf-8")
        framework_lines = []
        for key, value in session.framework_output.items():
            framework_lines.append(f"### {key.replace('_', ' ').title()}")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        framework_lines.append(f"- **{sub_key}:**")
                        framework_lines.extend(f"  - {item}" for item in sub_value)
                    else:
                        framework_lines.append(f"- **{sub_key}:** {sub_value}")
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        framework_lines.append(f"- {item}")
                    else:
                        framework_lines.append(f"- {item}")
        options_text = "\n".join(
            f"- **{option.name}** ({option.score_estimate}/10): {option.summary}"
            for option in session.options
        )
        rejected = rejected_alternatives or [opt for opt in session.options if opt.rejected_reason]
        rejected_text = "\n".join(
            f"- {option.name}: rejected because {option.rejected_reason}" for option in rejected
        ) or "- None documented"
        assumptions_text = "\n".join(f"- {item}" for item in session.assumptions)
        trade_offs_text = "\n".join(f"- {item}" for item in session.trade_offs)
        estimates_text = "\n".join(f"- **{key}:** {value}" for key, value in session.quantified_estimates.items())
        answers_text = "\n".join(f"- {key}: {value}" for key, value in session.clarifying_answers.items())

        return (
            template.replace("{{topic}}", session.topic)
            .replace("{{session_id}}", session.session_id)
            .replace("{{framework}}", session.framework)
            .replace("{{date}}", datetime.now(UTC).date().isoformat())
            .replace("{{clarifying_summary}}", answers_text or "Pending user answers")
            .replace("{{framework_output}}", "\n".join(framework_lines) or "Pending framework application")
            .replace("{{assumptions}}", assumptions_text or "- None stated")
            .replace("{{options}}", options_text or "- Pending")
            .replace("{{recommendation}}", session.recommendation or "Pending clarification")
            .replace("{{trade_offs}}", trade_offs_text or "- None stated")
            .replace("{{rejected_alternatives}}", rejected_text)
            .replace("{{quantified_estimates}}", estimates_text or "- Pending quantification")
        )

    def build_strategy_playbook(self) -> PlaybookGraph:
        graph = PlaybookGraph("compass-strategy")

        async def clarify_node(state: dict[str, Any]) -> dict[str, Any]:
            topic = state.get("topic", "Untitled strategy")
            session = self.start_session(topic, framework=state.get("framework", StrategyFramework.SWOT))
            state["clarifying_questions"] = session.clarifying_questions
            state["session_id"] = session.session_id
            return state

        async def synthesize_node(state: dict[str, Any]) -> dict[str, Any]:
            answers = dict(state.get("answers", {}))
            if not has_sufficient_clarification(answers):
                state["ready_for_recommendation"] = False
                state["reason"] = f"Need at least {MIN_CLARIFYING_QUESTIONS} clarifying answers"
                return state
            session = self.formulate_recommendation(
                state.get("topic", ""),
                framework=state.get("framework", StrategyFramework.SWOT),
                answers=answers,
                assumptions=list(state.get("assumptions", [])),
            )
            state.update(session.to_dict())
            return state

        async def publish_node(state: dict[str, Any]) -> dict[str, Any]:
            if not state.get("ready_for_recommendation"):
                return state
            markdown = state.get("markdown", "")
            doc = workspace_repo.create_document(
                self._user,
                title=f"Strategy: {state.get('topic', 'Session')}",
                content=markdown,
                tags=["compass-strategy", f"framework:{state.get('framework', 'swot')}"],
            )
            state["document_id"] = doc.get("id")
            return state

        graph.add_node("clarify", clarify_node)
        graph.add_node("synthesize", synthesize_node)
        graph.add_node("publish", publish_node)
        graph.add_edge("clarify", "synthesize")
        graph.add_edge("synthesize", "publish")
        graph.add_edge("publish", END)
        return graph

    async def run_strategy_session(
        self,
        topic: str,
        *,
        framework: str = StrategyFramework.SWOT,
        answers: dict[str, str] | None = None,
        assumptions: list[str] | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        graph = self.build_strategy_playbook()
        runner = PlaybookRunner(graph.compile())
        initial_state = {
            "workspace_id": self.workspace_id,
            "topic": topic,
            "framework": framework,
            "answers": answers or {},
            "assumptions": assumptions or [],
        }
        run = await runner.execute_inline(initial_state)
        result = dict(run.state)
        if store and result.get("ready_for_recommendation") and result.get("markdown") and not result.get("document_id"):
            doc = workspace_repo.create_document(
                self._user,
                title=f"Strategy: {topic}",
                content=result["markdown"],
                tags=["compass-strategy", f"framework:{framework}"],
            )
            result["document_id"] = doc.get("id")
        result["playbook_status"] = run.status.value
        return result
