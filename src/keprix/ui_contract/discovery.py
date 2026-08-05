"""Discovery card system for the Keprix home page.

Discovery cards are contextual prompts that help users find features
they have not yet encountered. One card is shown at a time. Dismissed
cards do not reappear for 30 days. A card that has been acted on
(user visited the target page) does not reappear.

Priority order (highest first):
  1. Quota >80%              (billing urgency)
  2. Brain health score <60  (data hygiene)
  3. Brain not visited and memories >=10
  4. Skills=0 and sessions >=5
  5. Voice not provisioned and workspace >=30 days old
  6. Tasks completed and no playbooks
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiscoveryCard:
    """A single discoverable feature card."""
    id: str
    condition_description: str
    text: str
    action_label: str
    target_path: str
    priority: int


DISCOVERY_CARDS: list[DiscoveryCard] = [
    DiscoveryCard(
        id="quota_warning",
        condition_description="quota_pct > 80",
        text="You are using {quota_pct}% of your monthly token budget.",
        action_label="Manage billing",
        target_path="/settings/billing",
        priority=1,
    ),
    DiscoveryCard(
        id="brain_health_low",
        condition_description="brain_health_score < 60",
        text="Your brain has {orphaned_node_count} orphaned nodes. Clean them up.",
        action_label="Open Brain Health",
        target_path="/brain/health",
        priority=2,
    ),
    DiscoveryCard(
        id="discover_brain",
        condition_description="memories >= 10 and brain_never_opened",
        text="Your agent has remembered {memory_count} things. See them as a graph.",
        action_label="Open brain graph",
        target_path="/brain/graph",
        priority=3,
    ),
    DiscoveryCard(
        id="discover_skills",
        condition_description="sessions >= 5 and skills_count == 0",
        text="Your agent hasn't learned any reusable skills yet. Add one.",
        action_label="Add a skill",
        target_path="/skills",
        priority=4,
    ),
    DiscoveryCard(
        id="discover_voice",
        condition_description="voice_not_provisioned and workspace_age_days >= 30",
        text="Give your agent a phone number so clients can call it directly.",
        action_label="Set up voice",
        target_path="/voice",
        priority=5,
    ),
    DiscoveryCard(
        id="discover_playbooks",
        condition_description="tasks_completed > 0 and playbooks_count == 0",
        text="You have completed tasks. Turn them into repeatable playbooks.",
        action_label="Open playbook builder",
        target_path="/tasks/playbooks/new",
        priority=6,
    ),
]

DISCOVERY_CARDS_BY_ID: dict[str, DiscoveryCard] = {c.id: c for c in DISCOVERY_CARDS}
DISCOVERY_CARDS_BY_PRIORITY: list[DiscoveryCard] = sorted(
    DISCOVERY_CARDS, key=lambda c: c.priority
)


def select_card(
    context: dict,
    dismissed_ids: set[str] | None = None,
    acted_on_ids: set[str] | None = None,
) -> DiscoveryCard | None:
    """Select the highest-priority applicable discovery card.

    Args:
        context: Dict with workspace signal values. Known keys:
            quota_pct (int), brain_health_score (int), memories (int),
            brain_never_opened (bool), sessions (int), skills_count (int),
            voice_not_provisioned (bool), workspace_age_days (int),
            tasks_completed (int), playbooks_count (int).
        dismissed_ids: Card IDs the user has dismissed.
        acted_on_ids: Card IDs the user has already acted on.

    Returns the first card whose condition is satisfied, or None.
    """
    dismissed = dismissed_ids or set()
    acted = acted_on_ids or set()
    skip = dismissed | acted

    for card in DISCOVERY_CARDS_BY_PRIORITY:
        if card.id in skip:
            continue
        if _evaluate(card, context):
            return card
    return None


def _evaluate(card: DiscoveryCard, ctx: dict) -> bool:
    cid = card.id
    if cid == "quota_warning":
        return int(ctx.get("quota_pct", 0)) > 80
    if cid == "brain_health_low":
        return int(ctx.get("brain_health_score", 100)) < 60
    if cid == "discover_brain":
        return (
            int(ctx.get("memories", 0)) >= 10
            and bool(ctx.get("brain_never_opened", False))
        )
    if cid == "discover_skills":
        return (
            int(ctx.get("sessions", 0)) >= 5
            and int(ctx.get("skills_count", 0)) == 0
        )
    if cid == "discover_voice":
        return (
            bool(ctx.get("voice_not_provisioned", False))
            and int(ctx.get("workspace_age_days", 0)) >= 30
        )
    if cid == "discover_playbooks":
        return (
            int(ctx.get("tasks_completed", 0)) > 0
            and int(ctx.get("playbooks_count", 0)) == 0
        )
    return False
