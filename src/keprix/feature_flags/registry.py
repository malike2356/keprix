"""Canonical registry of Keprix progressive-surface feature flags.

These flags gate common user/operator UI surfaces (nav and related pages).
They are intentionally not a 1:1 map of every backend package, plugin, or CLI module.
Admins/owners always receive the full navigation contract; use Settings → Modules
and Developer → Module inventory for the wider catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeatureFlagDef:
    id: str
    name: str
    description: str
    category: str
    default: bool
    tags: list[str] = field(default_factory=list)


KNOWN_FLAGS: list[FeatureFlagDef] = [
    # --- Interface ---
    FeatureFlagDef(
        id="voice_input",
        name="Voice Input",
        description="Voice transcription and AI voice assistant features.",
        category="interface",
        default=False,
    ),
    FeatureFlagDef(
        id="simplified_mode",
        name="Simplified Mode",
        description="Show a condensed, non-technical UI layout. Useful for non-developer users.",
        category="interface",
        default=False,
    ),
    # --- Workspace ---
    FeatureFlagDef(
        id="data_workspace",
        name="Data Workspace",
        description="Data pipeline, RAG ingestion, and structured knowledge tools.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="opportunity_engine",
        name="Opportunity Engine",
        description="CRM contacts, leads, and opportunity pipeline.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="playbooks",
        name="Playbooks",
        description="Automated workflow builder and playbook runner.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="research",
        name="Research Projects",
        description="AI-assisted research workspace and project management.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="calendar",
        name="Calendar",
        description="Integrated calendar and scheduling.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="email",
        name="Email",
        description="Email client and AI compose tools.",
        category="workspace",
        default=True,
    ),
    FeatureFlagDef(
        id="channel_shield",
        name="Channel Shield",
        description="Shared inbound protection across email and messaging channels.",
        category="security",
        default=True,
    ),
    FeatureFlagDef(
        id="contacts",
        name="Contacts",
        description="Contact management and sync (Google, iCloud, etc.).",
        category="workspace",
        default=True,
    ),
    # --- Apps and Automation ---
    FeatureFlagDef(
        id="agent_apps",
        name="Agent Apps Marketplace",
        description="Third-party agent application marketplace and installer.",
        category="apps",
        default=True,
    ),
    FeatureFlagDef(
        id="builder",
        name="Job Builder",
        description="Background job scheduling and management interface.",
        category="apps",
        default=True,
    ),
    FeatureFlagDef(
        id="browser",
        name="Built-in Browser",
        description="AI-controlled in-app browser for web automation.",
        category="apps",
        default=True,
    ),
    # --- Developer ---
    FeatureFlagDef(
        id="evals",
        name="Evaluations",
        description="Agent evaluation, benchmarking, and output scoring.",
        category="developer",
        default=True,
    ),
    FeatureFlagDef(
        id="coding",
        name="Coding Tools",
        description="AI coding assistant, ladder, and code generation.",
        category="developer",
        default=True,
    ),
    # --- Security ---
    FeatureFlagDef(
        id="governance",
        name="Scout Governance",
        description="External Scout kill-switch, audit trail, and operator policy panel.",
        category="security",
        default=False,
    ),
    # --- Commerce ---
    FeatureFlagDef(
        id="commerce",
        name="Billing and Commerce",
        description="Subscription management, plan upgrades, and Stripe billing UI.",
        category="admin",
        default=False,
    ),
]

FLAG_BY_ID: dict[str, FeatureFlagDef] = {f.id: f for f in KNOWN_FLAGS}
