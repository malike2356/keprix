from pathlib import Path

from keprix.coding.ladder_debt import add_debt, harvest_debt, list_debt, resolve_debt


def test_ladder_debt_add_resolve_and_harvest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    source = tmp_path / "src" / "demo.py"
    source.parent.mkdir()
    source.write_text("# ponytail: naive scan; ceiling 100 rows; upgrade to index\n", encoding="utf-8")

    manual = add_debt("Replace wrapper with lru_cache")
    harvested = harvest_debt(tmp_path / "src")
    resolved = resolve_debt(manual.id)

    assert harvested
    assert resolved is not None and resolved.status == "resolved"
    assert len(list_debt()) == 2
