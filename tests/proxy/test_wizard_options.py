"""Credential setup option tests."""

from __future__ import annotations

from keprix.setup.wizard import credential_management_options


def test_credential_management_options_mark_legacy_paths() -> None:
    options = {row["id"]: row for row in credential_management_options()}

    assert options["external_vault"]["recommended"] is True
    assert options["cordon"]["legacy"] is False
    assert options["keprix_vault"]["legacy"] is True
    assert options["env"]["legacy"] is True
