"""Prompt 38 and Scout governance onboarding copy guards."""

from __future__ import annotations

import subprocess
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
GOVERNANCE_PAGE = FRONTEND_SRC / "app" / "(workspace)" / "settings" / "governance" / "page.tsx"


def _rg(pattern: str, path: Path | None = None) -> list[str]:
    target = str(path or FRONTEND_SRC)
    result = subprocess.run(
        ["rg", "-n", pattern, target],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_governance_page_exists() -> None:
    assert GOVERNANCE_PAGE.is_file()


def test_governance_page_has_scout_onboarding_copy() -> None:
    text = GOVERNANCE_PAGE.read_text(encoding="utf-8")
    assert "How to connect Scout" in text
    assert "Connect Scout" in text
    assert "labyrinthscout.com/pricing" in text
    assert "Scout is a paid service. keprix works without it." in text
    assert "Get your API key from the Scout console after purchase" in text
    assert "One API key governs this entire keprix deployment" in text
    assert "Individual agents do not get separate Scout keys" in text
    assert "Not available in keprix yet" in text
    assert 'No OAuth or "Sign in with Scout"' in text
    assert "No automatic key fetch after purchase" in text
    assert "No in-app Scout signup or billing" in text
    assert "No per-agent Scout keys" in text


def test_governance_connect_dialog_has_helper_copy() -> None:
    text = GOVERNANCE_PAGE.read_text(encoding="utf-8")
    assert "api.labyrinthscout.com" in text
    assert "provisioning email or Scout console" in text
    assert "never saved in plain text config" in text
    assert "Paste the key from the Scout console or provisioning email" in text


def test_governance_page_has_no_petraclus_upsell() -> None:
    text = GOVERNANCE_PAGE.read_text(encoding="utf-8").lower()
    assert "petraclus" not in text
    assert "discount" not in text


def test_scout_connector_not_surfaced_as_global_banner() -> None:
    hits = _rg(r"Connect Scout", FRONTEND_SRC / "components")
    assert hits == []
