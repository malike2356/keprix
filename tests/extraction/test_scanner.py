"""Extraction scanner tests."""

from __future__ import annotations

from pathlib import Path

from keprix.extraction.scanner import scan_reference_file, scan_reference_tree


def test_scan_skips_env_files(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('SECRET="sk-abcdefghijklmnopqrstuvwxyz1234"\n', encoding="utf-8")
    assert scan_reference_file(env_file) == []


def test_scan_detects_secrets_in_reference_tree(tmp_path: Path) -> None:
    pack = tmp_path / "sample"
    pack.mkdir()
    (pack / "config.ts").write_text('const key = "sk-abcdefghijklmnopqrstuvwxyz1234";\n', encoding="utf-8")
    findings = scan_reference_tree(pack)
    assert any(item.kind == "secret" for item in findings)


def test_customer_data_path_excluded_in_scanner(tmp_path: Path) -> None:
    tenant_dir = tmp_path / "tenant-data" / "acme"
    tenant_dir.mkdir(parents=True)
    data_file = tenant_dir / "records.json"
    data_file.write_text('{"email":"user@example.com"}', encoding="utf-8")
    findings = scan_reference_file(data_file)
    assert any(item.kind == "customer_data" for item in findings)
