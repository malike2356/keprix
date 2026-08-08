"""Map shipped Keprix modules to GUI routes (or mark CLI/API-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .discovery import FEATURE_REGISTRY, FeatureDiscovery, FeatureInfo
from .context import installed_keprix_version


@dataclass(frozen=True)
class GuiModule:
    id: str
    name: str
    description: str
    module: str
    version: str
    gui_href: str | None
    gui_status: str  # available | partial | cli_api | missing_gui | integration
    category: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# Extra built capabilities that are easy to miss in the sidebar.
_EXTRA_MODULES: tuple[GuiModule, ...] = (
    GuiModule(
        id="channel_shield",
        name="Channel Shield",
        description="Shared inbound protection across email, Slack, Teams, Telegram, WhatsApp, Discord, SMS, and web.",
        module="keprix.channel_shield",
        version="0.16.0",
        gui_href="/channel-shield",
        gui_status="available",
        category="security",
    ),
    GuiModule(
        id="email_imap",
        name="Native email (IMAP/SMTP)",
        description="Connect inbox accounts, sync mail, and draft AI replies.",
        module="keprix.email",
        version="0.16.0",
        gui_href="/email",
        gui_status="available",
        category="channels",
    ),
    GuiModule(
        id="web_search",
        name="Web search providers",
        description="Tavily, SearXNG, and other research search backends.",
        module="keprix.api.web_search_settings",
        version="0.16.0",
        gui_href="/settings/web-search",
        gui_status="available",
        category="research",
    ),
    GuiModule(
        id="channels_admin",
        name="Messaging channels",
        description="Telegram and other gateway channel configuration.",
        module="keprix.gateway",
        version="0.16.0",
        gui_href="/dashboard/channels",
        gui_status="available",
        category="channels",
    ),
    GuiModule(
        id="sso_linking",
        name="SSO account linking",
        description="Link Google, GitHub, or OIDC to a workspace account.",
        module="keprix.auth.sso",
        version="0.16.0",
        gui_href="/settings/account/connected-accounts",
        gui_status="available",
        category="security",
    ),
    GuiModule(
        id="agent_os",
        name="Agent OS",
        description="Audits, skill proposals, action board, and client kits.",
        module="keprix.agent_os",
        version="0.16.0",
        gui_href="/agent-os",
        gui_status="available",
        category="automations",
    ),
    GuiModule(
        id="playbooks",
        name="Playbooks studio",
        description="Visual playbook authoring and publish flow.",
        module="keprix.playbooks",
        version="0.16.0",
        gui_href="/playbooks",
        gui_status="available",
        category="automations",
    ),
    GuiModule(
        id="rag_pipeline",
        name="RAG pipelines",
        description="Document ingestion and retrieval pipelines.",
        module="keprix.rag",
        version="0.16.0",
        gui_href="/rag-pipeline",
        gui_status="available",
        category="data",
    ),
    GuiModule(
        id="browser_harness",
        name="Browser harness",
        description="Agent browser sessions and encrypted profiles.",
        module="keprix.browser",
        version="0.16.0",
        gui_href="/settings/browser",
        gui_status="available",
        category="automations",
    ),
    GuiModule(
        id="control_center",
        name="Control center",
        description="Operator copilot and runtime controls.",
        module="keprix.control_center",
        version="0.16.0",
        gui_href="/control-center",
        gui_status="available",
        category="security",
    ),
    GuiModule(
        id="evals",
        name="Evals",
        description="Model and skill evaluation runs.",
        module="keprix.providers.evals",
        version="0.16.0",
        gui_href="/evals",
        gui_status="available",
        category="research",
    ),
    GuiModule(
        id="tool_acl",
        name="Tool ACL",
        description="Product and resource ACL admin console.",
        module="keprix.security.acl",
        version="0.16.0",
        gui_href="/admin/tool-acl",
        gui_status="available",
        category="security",
    ),
    GuiModule(
        id="fleet_admin",
        name="Fleet admin",
        description="Enterprise fleet instance register and health.",
        module="keprix.fleet",
        version="0.16.0",
        gui_href="/admin/fleet",
        gui_status="available",
        category="admin",
    ),
    GuiModule(
        id="companion_pairing",
        name="Companion pairing",
        description="Mobile companion QR pairing.",
        module="keprix.mobile.companion",
        version="0.16.0",
        gui_href="/admin/companion",
        gui_status="available",
        category="admin",
    ),
    GuiModule(
        id="data_plane_datasets",
        name="Data plane datasets",
        description="Catalog import query for /api/data.",
        module="keprix.data_plane",
        version="0.16.0",
        gui_href="/data?tab=datasets",
        gui_status="available",
        category="data",
    ),
    GuiModule(
        id="jobs_queue",
        name="Jobs queue",
        description="Local background job ops.",
        module="keprix.jobs",
        version="0.16.0",
        gui_href="/data?tab=jobs",
        gui_status="available",
        category="data",
    ),
    GuiModule(
        id="ml_workspace",
        name="ML workspace",
        description="Experiments and model registry.",
        module="keprix.ml_workspace",
        version="0.16.0",
        gui_href="/data?tab=ml",
        gui_status="available",
        category="data",
    ),
    GuiModule(
        id="document_export",
        name="Document export",
        description="Cover and signatory exports.",
        module="keprix.export",
        version="0.16.0",
        gui_href="/data?tab=export",
        gui_status="available",
        category="data",
    ),
    GuiModule(
        id="improvement_loop",
        name="Improvement proposals",
        description="Auto-improvement Soft Wall review.",
        module="keprix.improvement",
        version="0.16.0",
        gui_href="/agent-os/improvements",
        gui_status="available",
        category="automations",
    ),
    GuiModule(
        id="public_v1_api",
        name="Public /v1 API",
        description="Integration API intentionally without workspace GUI.",
        module="keprix.public_api",
        version="0.16.0",
        gui_href=None,
        gui_status="integration",
        category="integration",
    ),
    GuiModule(
        id="slash_tui",
        name="Slash / TUI",
        description="CLI and TUI operator surfaces; intentional non-GUI.",
        module="keprix.keprix_cli",
        version="0.16.0",
        gui_href=None,
        gui_status="cli_api",
        category="cli",
    ),
)

_FEATURE_GUI: dict[str, tuple[str | None, str, str]] = {
    # name -> (href, status, category)
    "billing": ("/settings/billing", "available", "commerce"),
    "governance": ("/settings/governance", "available", "security"),
    "combo_routing": ("/dashboard/settings", "available", "providers"),
    "compression": ("/dashboard/settings", "available", "providers"),
    "guardrails": ("/dashboard/settings", "available", "providers"),
    "a2a": ("/a2a", "available", "automations"),
    "observability": ("/observability", "available", "data"),
    "notion": ("/integrations?id=notion", "available", "integrations"),
    "semantic_cache": ("/dashboard/settings", "available", "providers"),
    "cli_auto_config": (None, "cli_api", "cli"),
}


def _from_feature(info: FeatureInfo) -> GuiModule:
    href, status, category = _FEATURE_GUI.get(info.name, (None, "cli_api", "modules"))
    return GuiModule(
        id=info.name,
        name=info.name.replace("_", " ").title(),
        description=info.description,
        module=info.module,
        version=info.version,
        gui_href=href,
        gui_status=status,
        category=category,
    )


def list_gui_modules(*, installed_version: str | None = None) -> list[GuiModule]:
    """Return modules shipped up to the installed version, plus always-on extras."""
    version = installed_version or installed_keprix_version()
    discovery = FeatureDiscovery()
    features = discovery.get_new_features("0.0.0", version)
    seen: set[str] = set()
    modules: list[GuiModule] = []
    for info in features:
        if info.name in seen:
            continue
        seen.add(info.name)
        modules.append(_from_feature(info))
    for extra in _EXTRA_MODULES:
        if extra.id in seen:
            continue
        seen.add(extra.id)
        modules.append(extra)
    return modules


def modules_payload(*, installed_version: str | None = None) -> dict[str, object]:
    version = installed_version or installed_keprix_version()
    modules = list_gui_modules(installed_version=version)
    missing_gui = [m.to_dict() for m in modules if m.gui_status in {"missing_gui", "cli_api", "partial", "integration"}]
    return {
        "installed_version": version,
        "modules": [m.to_dict() for m in modules],
        "missing_gui": missing_gui,
        "counts": {
            "total": len(modules),
            "available": sum(1 for m in modules if m.gui_status == "available"),
            "partial": sum(1 for m in modules if m.gui_status == "partial"),
            "cli_api": sum(1 for m in modules if m.gui_status == "cli_api"),
            "missing_gui": sum(1 for m in modules if m.gui_status == "missing_gui"),
            "integration": sum(1 for m in modules if m.gui_status == "integration"),
        },
        "registry_versions": sorted(FEATURE_REGISTRY.keys()),
    }
