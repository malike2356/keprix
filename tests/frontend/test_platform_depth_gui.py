"""Frontend smoke for platform depth GUIs (488-496)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_improvement_gui_and_routes() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/agent-os/improvements/page.tsx").read_text(
        encoding="utf-8"
    )
    api = (ROOT / "frontend/src/lib/improvement-api.ts").read_text(encoding="utf-8")
    routes = (ROOT / "src/keprix/improvement/routes.py").read_text(encoding="utf-8")
    assert "Soft Wall apply" in page
    assert "/api/improvement/proposals" in api
    assert "reject_proposal" in routes and "apply_proposal" in routes
    settings = (
        ROOT / "frontend/src/app/(workspace)/settings/agent/self-improvement/page.tsx"
    ).read_text(encoding="utf-8")
    assert "/agent-os/improvements" in settings


def test_platform_admin_pages_exist() -> None:
    for rel in (
        "admin/code-agent/page.tsx",
        "admin/typed-agents/page.tsx",
        "admin/kernel/page.tsx",
        "admin/interfaces/page.tsx",
        "admin/intent/page.tsx",
        "admin/tool-adapters/page.tsx",
        "admin/personas/page.tsx",
    ):
        path = ROOT / "frontend/src/app/(workspace)" / rel
        assert path.is_file(), rel
        text = path.read_text(encoding="utf-8")
        assert "PageHeader" in text


def test_typed_agents_gui_is_operator_ready() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/admin/typed-agents/page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/lib/platform-admin-api.ts").read_text(encoding="utf-8")
    routes = (ROOT / "src/keprix/typed_agents/routes.py").read_text(encoding="utf-8")
    assert "Export schema JSON" in page
    assert "Soft Wall run" in page
    assert "SkeletonTable" in page
    assert "inventory" in page
    assert "runTypedAgent" in api
    assert "inventory" in routes


def test_evals_benchmarks_wired() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/evals/page.tsx").read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/lib/evals-benchmarks-api.ts").read_text(encoding="utf-8")
    assert "runBenchmarkAll" in page
    assert "/api/evals/benchmarks" in api


def test_platform_nav_synced() -> None:
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    for href in (
        "/agent-os/improvements",
        "/admin/code-agent",
        "/admin/typed-agents",
        "/admin/kernel",
        "/admin/interfaces",
        "/admin/intent",
        "/admin/tool-adapters",
        "/admin/personas",
    ):
        assert href in py, href
        assert href in ts, href
