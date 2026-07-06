"""Prompt 21 acceptance guards for the Keprix frontend."""

from __future__ import annotations

import subprocess
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _rg(pattern: str) -> list[str]:
    result = subprocess.run(
        ["rg", "-n", pattern, str(FRONTEND_SRC)],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_no_commercial_branding_domains():
    assert _rg(r"aiva\.co\.uk|hireaiva") == []


def test_no_enterprise_plan_guards():
    assert _rg(r"requireTeamPlan|requireEnterprisePlan") == []


def test_no_better_auth_imports():
    assert _rg(r"better-auth") == []


def test_launcher_and_feature_pages_exist():
    required = [
        "app/(workspace)/launcher/page.tsx",
        "app/(workspace)/research/page.tsx",
        "app/(workspace)/compare/page.tsx",
        "app/(workspace)/email/page.tsx",
        "app/(workspace)/playbook/page.tsx",
        "app/(workspace)/gallery/page.tsx",
        "app/(workspace)/vault/page.tsx",
        "app/(workspace)/admin/cron/page.tsx",
        "app/(workspace)/admin/mcp/page.tsx",
        "app/(workspace)/admin/backup/page.tsx",
        "app/onboarding/page.tsx",
        "lib/ce-api.ts",
        "lib/ce-auth.tsx",
        "components/chat/CanvasPanel.tsx",
        "app/api/themes/route.ts",
    ]
    for relative in required:
        assert (FRONTEND_SRC / relative).is_file(), relative
