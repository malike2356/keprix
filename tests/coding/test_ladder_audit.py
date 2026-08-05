from pathlib import Path

from keprix.coding.ladder_audit import audit_repo


def test_ladder_audit_finds_debt_marker(tmp_path: Path) -> None:
    target = tmp_path / "demo.py"
    target.write_text("# ponytail: temporary O(n^2), upgrade when >100 rows\n", encoding="utf-8")

    result = audit_repo(tmp_path)

    assert result["estimated_lines_removable"] > 0
