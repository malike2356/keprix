"""Agent OS onboarding checklist definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OnboardingStep:
    id: str
    level: int
    title: str
    action_url: str
    auto_complete: str
    copy: str = ""
    track: str = "maturity"  # activation | maturity

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        id="a1_provider",
        level=0,
        title="Connect an LLM provider",
        action_url="/auth/setup",
        auto_complete="provider.connected",
        copy="Add an API key so chat and tools can run.",
        track="activation",
    ),
    OnboardingStep(
        id="a2_first_chat",
        level=0,
        title="Send your first chat message",
        action_url="/chat",
        auto_complete="chat.first_message",
        copy="Confirm the agent responds in the workspace.",
        track="activation",
    ),
    OnboardingStep(
        id="a2b_hello_world",
        level=0,
        title="Run the Hello World workflow (Day 1)",
        action_url="/agent-apps",
        auto_complete="hello_world.completed",
        copy="One command: keprix agent-os hello. First result in minutes; note lands in the vault.",
        track="activation",
    ),
    OnboardingStep(
        id="a3_channel",
        level=0,
        title="Connect a messaging channel (optional)",
        action_url="/dashboard/channels",
        auto_complete="channel.connected",
        copy="Telegram, Discord, or email so Keprix can reach you outside the browser.",
        track="activation",
    ),
    OnboardingStep(
        id="a3b_vault",
        level=0,
        title="Confirm the single vault (Day 1)",
        action_url="/settings/vault",
        auto_complete="vault.configured",
        copy="One vault for all agents. Conversations auto-capture into conversations/.",
        track="activation",
    ),
    OnboardingStep(
        id="l0_onboard",
        level=0,
        title="Complete the onboard interview (Day 1)",
        action_url="/agent-os/onboard",
        auto_complete="onboard.completed",
        copy="Default shift - ask how AI could do 30% before manual work.",
        track="maturity",
    ),
    OnboardingStep("l1_audit", 1, "Complete a workflow audit", "/agent-os/audit", "audit.completed", track="maturity"),
    OnboardingStep("l1_first_skill", 1, "Approve your first skill proposal", "/agent-os/skill-proposals", "skill_proposal.approved", track="maturity"),
    OnboardingStep("l1_promote", 1, "Promote a skill to an automation", "/agent-os/promote", "automation.promoted", track="maturity"),
    OnboardingStep("l1_baseline", 1, "Set a loop baseline on an automation", "/agent-os/loop-profiles", "loop_profile.baseline_set", track="maturity"),
    OnboardingStep("l2_workspace", 2, "Create a Knowledge Pipeline workspace", "/workspace/new", "workspace.created_with_template", track="maturity"),
    OnboardingStep("l2_connect_one", 2, "Wire your first connection (Day 2)", "/agent-os/connections", "connections.domain_live", track="maturity"),
    OnboardingStep("l2_four_cs_audit", 2, "Run a Four C's maturity audit (Day 7)", "/agent-os/maturity", "maturity_audit.completed", track="maturity"),
    OnboardingStep("l2_wiki", 2, "Add your first wiki article", "/documents", "vault.file_in_wiki", track="maturity"),
    OnboardingStep("l3_pin", 3, "Pin an action on the board", "/agent-os", "action_board.pin_added", track="maturity"),
    OnboardingStep("l3_headless", 3, "Run an action headless", "/agent-os", "headless_run.completed", track="maturity"),
    OnboardingStep("l3_schedule", 3, "Schedule a recurring action", "/agent-os", "cron.created_from_skill", track="maturity"),
    OnboardingStep("l4_kit", 4, "Export a client kit OR invite a teammate", "/settings/agent-os/client-kit", "client_kit.exported OR user.invited", track="maturity"),
)

STEP_BY_ID = {step.id: step for step in STEPS}
EVENT_TO_STEP_IDS: dict[str, tuple[str, ...]] = {}
for step in STEPS:
    for event_name in (part.strip() for part in step.auto_complete.split(" OR ")):
        EVENT_TO_STEP_IDS.setdefault(event_name, tuple())
        EVENT_TO_STEP_IDS[event_name] = (*EVENT_TO_STEP_IDS[event_name], step.id)


def all_step_ids() -> list[str]:
    return [step.id for step in STEPS]


def activation_step_ids() -> list[str]:
    return [step.id for step in STEPS if step.track == "activation"]


def steps_payload() -> list[dict[str, object]]:
    return [step.to_dict() for step in STEPS]
