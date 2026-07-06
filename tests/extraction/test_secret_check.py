"""Extraction secret check tests."""

from __future__ import annotations

from pathlib import Path

from keprix.extraction.secret_check import has_secret_content, scan_file, scan_text


def test_secret_patterns_are_rejected() -> None:
    sample = 'API_KEY="sk-abcdefghijklmnopqrstuvwxyz1234"'
    assert scan_text(sample)
    assert has_secret_content(sample)


def test_secret_file_scan_fails(tmp_path: Path) -> None:
    secret_file = tmp_path / "secrets.env"
    secret_file.write_text('TOKEN="sk-abcdefghijklmnopqrstuvwxyz1234"\n', encoding="utf-8")
    findings = scan_file(secret_file)
    assert findings["secrets"]


def test_pem_extension_blocked(tmp_path: Path) -> None:
    key_file = tmp_path / "private.pem"
    key_file.write_text("placeholder", encoding="utf-8")
    findings = scan_file(key_file)
    assert findings["blocked_extensions"]
