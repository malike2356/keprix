"""Hub scanner tests."""

from __future__ import annotations

from pathlib import Path

from keprix.hub.scanner import requires_approval, scan_pack_dir


def test_secret_scan_fails(tmp_path: Path) -> None:
    pack_dir = tmp_path / "bad-pack"
    pack_dir.mkdir()
    (pack_dir / "config.env").write_text('API_KEY="sk-abcdefghijklmnopqrstuvwxyz1234"\n', encoding="utf-8")
    findings = scan_pack_dir(pack_dir, [])
    assert findings["secrets"]


def test_risky_permission_requires_approval() -> None:
    assert requires_approval("high", {"permissions": ["shell:execute"]})
    assert not requires_approval("low", {"permissions": []})
