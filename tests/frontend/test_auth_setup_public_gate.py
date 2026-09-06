"""Real gap closed live (2026-09-06): the maintainer's own public
marketing/demo instance (keprixai.com/app.keprixai.com) served the real
first-run setup wizard at /auth/setup - the same page that creates THE
owner account and captures a live LLM provider key for whichever instance
serves it. Keprix does not offer hosted accounts, so an anonymous visitor
reaching that page there must see a message pointing them at their own
self-hosted install instead. See keprix.setup.wizard.is_public_setup_disabled().
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_wizard_module_exposes_public_setup_disabled() -> None:
    source = (ROOT / "src/keprix/setup/wizard.py").read_text(encoding="utf-8")
    assert "def is_public_setup_disabled" in source
    assert "KEPRIX_PUBLIC_SETUP_DISABLED" in source
    assert '"public_setup_disabled"' in source


def test_wizard_step_route_checks_the_flag_before_setup_complete() -> None:
    source = (ROOT / "src/keprix/setup/routes.py").read_text(encoding="utf-8")
    assert "is_public_setup_disabled" in source
    # Defense in depth: the public check must not be conditioned on
    # is_setup_complete() also being true - it has to stand on its own.
    public_check_idx = source.index("if is_public_setup_disabled():")
    setup_complete_idx = source.index("if is_setup_complete():")
    assert public_check_idx < setup_complete_idx


def test_auth_setup_page_shows_self_host_message_for_public_instances() -> None:
    page = (ROOT / "frontend/src/app/auth/setup/page.tsx").read_text(encoding="utf-8")
    assert "public_setup_disabled" in page
    assert "self-hosted product" in page.lower()
    assert "/download" in page
