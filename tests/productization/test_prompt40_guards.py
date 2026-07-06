"""Prompt 40 productization and brand guards."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_FRONTEND = ROOT / "frontend" / "src" / "app" / "(workspace)"
SHELL_COMPONENTS = ROOT / "frontend" / "src" / "components" / "shell"


def _rg(pattern: str, path: Path) -> list[str]:
    result = subprocess.run(
        ["rg", "-n", "-i", pattern, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_license_contains_required_text() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Verlox Limited" in text
    assert "keprix" in text


def test_third_party_notices_exists() -> None:
    assert (ROOT / "THIRD_PARTY_NOTICES.md").is_file()
    assert "MIT" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")


def test_acknowledgments_file_removed() -> None:
    assert not (ROOT / "ACKNOWLEDGMENTS.md").exists()


def test_workspace_ui_has_no_upstream_agent_names() -> None:
    pattern = r"openclaw|hermes.agent|odysseus-ai|\bOdysseus\b|\bHermes\b|\bOpenClaw\b"
    hits = _rg(pattern, WORKSPACE_FRONTEND) + _rg(pattern, SHELL_COMPONENTS)
    assert hits == []


def test_workspace_ui_has_no_carina_ce_branding() -> None:
    pattern = r"Carina CE|carina_ce|carina-ce|CARINA_CE"
    hits = _rg(pattern, WORKSPACE_FRONTEND) + _rg(pattern, SHELL_COMPONENTS)
    assert hits == []


def test_workspace_footer_copy() -> None:
    footer = (SHELL_COMPONENTS / "WorkspaceFooter.tsx").read_text(encoding="utf-8")
    assert "keprix - Community Edition" in footer
    assert "VERLOX Ltd" in footer


def test_cli_community_banner_text() -> None:
    from keprix_cli.banner import print_community_edition_banner
    import io
    import contextlib

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        print_community_edition_banner()
    output = buffer.getvalue()
    assert "The keprix Agent" in output
    assert "Community Edition" in output
    assert "labyrinthscout.com" in output


def test_release_docs_exist() -> None:
    for name in (
        "01-self-host.md",
        "02-configuration.md",
        "03-providers.md",
        "04-channels.md",
        "05-upgrade.md",
        "06-carina-aiva.md",
        "07-sdk.md",
        "08-keprix-agent.md",
        "09-license.md",
        "10-labyrinth-scout.md",
    ):
        assert (ROOT / "docs" / name).is_file(), name
