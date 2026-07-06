"""Decision frameworks and scenario planning for COMPASS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from keprix.personas.compass.persona import COMPASS_PERSONA
from keprix.workspace.repository import workspace_repo

MIN_CLARIFYING_QUESTIONS = 3


class ScenarioType(StrEnum):
    BEST = "best_case"
    WORST = "worst_case"
    LIKELY = "most_likely"


@dataclass(slots=True)
class DecisionCriterion:
    name: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight}


@dataclass(slots=True)
class DecisionOptionScore:
    name: str
    scores: dict[str, float]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "scores": dict(self.scores), "notes": self.notes}


@dataclass(slots=True)
class Scenario:
    name: str
    scenario_type: str
    probability_pct: float
    outcome_summary: str
    financial_impact_usd: int
    key_risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scenario_type": self.scenario_type,
            "probability_pct": self.probability_pct,
            "outcome_summary": self.outcome_summary,
            "financial_impact_usd": self.financial_impact_usd,
            "key_risks": list(self.key_risks),
        }


@dataclass
class DecisionMatrixResult:
    decision_id: str
    decision_title: str
    criteria: list[DecisionCriterion]
    options: list[DecisionOptionScore]
    weighted_totals: dict[str, float]
    recommendation: str
    alternatives: list[str]
    assumptions: list[str]
    clarifying_questions: list[str]
    scenarios: list[Scenario] = field(default_factory=list)
    premortem_risks: list[str] = field(default_factory=list)
    cost_benefit: dict[str, float] = field(default_factory=dict)
    document_id: str | None = None
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_title": self.decision_title,
            "criteria": [row.to_dict() for row in self.criteria],
            "options": [row.to_dict() for row in self.options],
            "weighted_totals": dict(self.weighted_totals),
            "recommendation": self.recommendation,
            "alternatives": list(self.alternatives),
            "assumptions": list(self.assumptions),
            "clarifying_questions": list(self.clarifying_questions),
            "scenarios": [row.to_dict() for row in self.scenarios],
            "premortem_risks": list(self.premortem_risks),
            "cost_benefit": dict(self.cost_benefit),
            "document_id": self.document_id,
            "markdown": self.markdown,
            "workspace_payload": self.to_workspace_payload(),
        }

    def to_workspace_payload(self) -> dict[str, Any]:
        return {
            "tables": [
                {
                    "name": "decision_matrix",
                    "columns": ["option", * [criterion.name for criterion in self.criteria], "weighted_total"],
                    "rows": [
                        {
                            "option": option.name,
                            **option.scores,
                            "weighted_total": self.weighted_totals.get(option.name, 0.0),
                        }
                        for option in self.options
                    ],
                }
            ],
            "charts": [
                {
                    "chart_id": "scenario-probability",
                    "chart_type": "bar",
                    "title": "Scenario probabilities",
                    "labels": [scenario.name for scenario in self.scenarios],
                    "series": [{"name": "Probability %", "data": [s.probability_pct for s in self.scenarios]}],
                }
            ],
        }


@dataclass
class ScenarioPlan:
    plan_id: str
    decision_title: str
    scenarios: list[Scenario]
    expected_value_usd: float
    assumptions: list[str]
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "decision_title": self.decision_title,
            "scenarios": [row.to_dict() for row in self.scenarios],
            "expected_value_usd": round(self.expected_value_usd, 2),
            "assumptions": list(self.assumptions),
            "markdown": self.markdown,
        }


def generate_decision_questions(decision_title: str) -> list[str]:
    return [
        f"What problem does '{decision_title}' solve if it succeeds?",
        "What is the cost of delaying this decision by one quarter?",
        "Which stakeholders must accept trade-offs for this to work?",
        "What evidence would change your mind after 30 days?",
    ][: max(MIN_CLARIFYING_QUESTIONS, 4)]


def normalize_weights(criteria: list[DecisionCriterion]) -> list[DecisionCriterion]:
    total = sum(row.weight for row in criteria) or 1.0
    return [DecisionCriterion(name=row.name, weight=round(row.weight / total, 3)) for row in criteria]


def score_weighted_totals(
    criteria: list[DecisionCriterion],
    options: list[DecisionOptionScore],
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for option in options:
        total = 0.0
        for criterion in criteria:
            total += option.scores.get(criterion.name, 0.0) * criterion.weight
        totals[option.name] = round(total, 2)
    return totals


class CompassDecisions:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = COMPASS_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._matrix_template = self.persona.prompts_dir / "decision_matrix.md"

    def build_scenarios(
        self,
        decision_title: str,
        *,
        base_impact_usd: int = 100_000,
    ) -> list[Scenario]:
        return [
            Scenario(
                name="Best case",
                scenario_type=ScenarioType.BEST,
                probability_pct=20.0,
                outcome_summary=f"{decision_title} exceeds plan with strong adoption",
                financial_impact_usd=int(base_impact_usd * 1.6),
                key_risks=["Execution must stay disciplined"],
            ),
            Scenario(
                name="Most likely",
                scenario_type=ScenarioType.LIKELY,
                probability_pct=55.0,
                outcome_summary=f"{decision_title} delivers moderate gains with manageable friction",
                financial_impact_usd=base_impact_usd,
                key_risks=["Competitive response within 2 quarters"],
            ),
            Scenario(
                name="Worst case",
                scenario_type=ScenarioType.WORST,
                probability_pct=25.0,
                outcome_summary=f"{decision_title} underperforms due to adoption and timing issues",
                financial_impact_usd=int(base_impact_usd * 0.4),
                key_risks=["Sunk cost", "Team morale impact", "Reputational drag"],
            ),
        ]

    def expected_value(self, scenarios: list[Scenario]) -> float:
        return sum((scenario.probability_pct / 100.0) * scenario.financial_impact_usd for scenario in scenarios)

    def run_premortem(self, decision_title: str) -> list[str]:
        return [
            f"Adoption for '{decision_title}' stalls after initial pilot",
            "Key dependency vendor changes pricing or terms",
            "Internal priorities shift before benefits materialise",
            "Success metrics are defined too late to correct course",
        ]

    def cost_benefit_summary(self, base_impact_usd: int) -> dict[str, float]:
        cost = round(base_impact_usd * 0.35, 2)
        benefit = float(base_impact_usd)
        return {
            "estimated_cost_usd": cost,
            "estimated_benefit_usd": benefit,
            "net_benefit_usd": round(benefit - cost, 2),
            "roi_pct": round(((benefit - cost) / cost) * 100, 1) if cost else 0.0,
        }

    def evaluate_decision(
        self,
        decision_title: str,
        *,
        criteria: list[DecisionCriterion] | None = None,
        options: list[DecisionOptionScore] | None = None,
        clarifying_answers: dict[str, str] | None = None,
        assumptions: list[str] | None = None,
        base_impact_usd: int = 100_000,
        store: bool = True,
    ) -> DecisionMatrixResult:
        questions = generate_decision_questions(decision_title)
        answers = clarifying_answers or {}
        answered = [value for value in answers.values() if value and value.strip()]

        normalized_criteria = normalize_weights(
            criteria
            or [
                DecisionCriterion("Impact", 0.35),
                DecisionCriterion("Feasibility", 0.25),
                DecisionCriterion("Cost", 0.20),
                DecisionCriterion("Risk", 0.20),
            ]
        )

        default_options = options or [
            DecisionOptionScore(
                name="Option A",
                scores={"Impact": 8.0, "Feasibility": 7.0, "Cost": 6.0, "Risk": 7.0},
                notes="Balanced path with moderate investment",
            ),
            DecisionOptionScore(
                name="Option B",
                scores={"Impact": 9.0, "Feasibility": 5.0, "Cost": 4.0, "Risk": 5.0},
                notes="Higher upside but harder execution",
            ),
            DecisionOptionScore(
                name="Option C",
                scores={"Impact": 6.0, "Feasibility": 8.0, "Cost": 8.0, "Risk": 8.0},
                notes="Low-risk incremental move",
            ),
        ]

        totals = score_weighted_totals(normalized_criteria, default_options)
        winner = max(totals, key=totals.get)
        runner_up = sorted(totals, key=totals.get, reverse=True)[1] if len(totals) > 1 else winner

        scenarios = self.build_scenarios(decision_title, base_impact_usd=base_impact_usd)
        premortem = self.run_premortem(decision_title)
        cost_benefit = self.cost_benefit_summary(base_impact_usd)

        result = DecisionMatrixResult(
            decision_id=str(uuid4()),
            decision_title=decision_title,
            criteria=normalized_criteria,
            options=default_options,
            weighted_totals=totals,
            recommendation=(
                f"Lean toward '{winner}' (score {totals[winner]}). "
                f"'{runner_up}' remains viable if feasibility constraints tighten."
            )
            if len(answered) >= MIN_CLARIFYING_QUESTIONS
            else (
                f"Answer at least {MIN_CLARIFYING_QUESTIONS} clarifying questions before finalising. "
                f"Provisional leader: '{winner}' (score {totals[winner]})."
            ),
            alternatives=[name for name in totals if name != winner],
            assumptions=assumptions
            or [
                "Scores reflect current information only",
                f"Expected value model uses ${base_impact_usd:,} baseline impact",
                "Probabilities are estimates, not forecasts",
            ],
            clarifying_questions=questions,
            scenarios=scenarios,
            premortem_risks=premortem,
            cost_benefit=cost_benefit,
        )
        result.markdown = self.render_matrix(result)

        if store and len(answered) >= MIN_CLARIFYING_QUESTIONS:
            doc = workspace_repo.create_document(
                self._user,
                title=f"Decision: {decision_title}",
                content=result.markdown,
                tags=["compass-decision", "decision-matrix"],
            )
            result.document_id = doc.get("id")

        return result

    def plan_scenarios(
        self,
        decision_title: str,
        *,
        base_impact_usd: int = 100_000,
        assumptions: list[str] | None = None,
    ) -> ScenarioPlan:
        scenarios = self.build_scenarios(decision_title, base_impact_usd=base_impact_usd)
        expected = self.expected_value(scenarios)
        assumptions_list = assumptions or [
            "Probabilities sum to 100%",
            "Financial impacts are annualised estimates",
        ]
        markdown_lines = [
            f"# Scenario Plan: {decision_title}",
            "",
            f"**Expected value (USD):** ${expected:,.0f}",
            "",
            "## Scenarios",
        ]
        for scenario in scenarios:
            markdown_lines.append(
                f"- **{scenario.name}** ({scenario.probability_pct}%): "
                f"{scenario.outcome_summary} | impact ${scenario.financial_impact_usd:,}"
            )
        markdown_lines.extend(["", "## Assumptions", ""])
        markdown_lines.extend(f"- {item}" for item in assumptions_list)

        return ScenarioPlan(
            plan_id=str(uuid4()),
            decision_title=decision_title,
            scenarios=scenarios,
            expected_value_usd=expected,
            assumptions=assumptions_list,
            markdown="\n".join(markdown_lines),
        )

    def render_matrix(self, result: DecisionMatrixResult) -> str:
        template = self._matrix_template.read_text(encoding="utf-8")
        criteria_table = "\n".join(f"| {row.name} | {row.weight:.2f} |" for row in result.criteria)
        score_header = "| Option | " + " | ".join(row.name for row in result.criteria) + " |"
        score_sep = "|---|" + "|".join("---" for _ in result.criteria) + "|"
        score_rows = []
        for option in result.options:
            cells = " | ".join(str(option.scores.get(criterion.name, 0.0)) for criterion in result.criteria)
            score_rows.append(f"| {option.name} | {cells} |")
        scores_table = "\n".join([score_header, score_sep, *score_rows])
        totals_table = "\n".join(f"- **{name}:** {score}" for name, score in result.weighted_totals.items())
        assumptions = "\n".join(f"- {item}" for item in result.assumptions)
        alternatives = "\n".join(f"- {name}" for name in result.alternatives)
        scenario_summary = "\n".join(
            f"- {scenario.name} ({scenario.probability_pct}%): ${scenario.financial_impact_usd:,}"
            for scenario in result.scenarios
        )

        return (
            template.replace("{{decision_title}}", result.decision_title)
            .replace("{{session_id}}", result.decision_id)
            .replace("{{date}}", datetime.now(UTC).date().isoformat())
            .replace("{{criteria_table}}", criteria_table)
            .replace("{{scores_table}}", scores_table)
            .replace("{{totals_table}}", totals_table)
            .replace("{{assumptions}}", assumptions)
            .replace("{{recommendation}}", result.recommendation)
            .replace("{{alternatives}}", alternatives)
            .replace("{{scenario_summary}}", scenario_summary)
        )
