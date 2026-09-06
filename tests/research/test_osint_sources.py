from keprix.research.osint.entity import Entity
from keprix.research.osint import sources


def test_default_sources_are_selected_by_entity_kind():
    assert list(sources.sources_for("company", ["wikipedia"])) == ["wikipedia"]
    assert "wayback" in sources.DEFAULT_SOURCES["domain"]


def test_source_adapter_normalizes_structured_csv_evidence(monkeypatch):
    def fake_invoke(name, entity, out_path, limit):
        assert name == "wikipedia"
        assert entity.name == "Ada Lovelace"
        assert limit == 3
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write("label,summary,wikipedia_url,qid\nAda Lovelace,Mathematician,https://en.wikipedia.org/wiki/Ada_Lovelace,Q42\n")
        return 1

    monkeypatch.setattr(sources, "_invoke", fake_invoke)
    rows = sources.make_source("wikipedia", limit=3)(Entity("person", "Ada Lovelace"))
    assert rows == [{
        "source": "wikipedia",
        "url": "https://en.wikipedia.org/wiki/Ada_Lovelace",
        "claim": "Mathematician",
        "qid": "Q42",
    }]


def test_source_adapter_returns_visible_error_without_fabricating_evidence(monkeypatch):
    def fail(*_args):
        raise TimeoutError("source timed out")

    monkeypatch.setattr(sources, "_invoke", fail)
    rows = sources.make_source("wikipedia")(Entity("person", "Ada Lovelace"))
    assert rows[0]["source"] == "wikipedia"
    assert "TimeoutError" in rows[0]["error"]
    assert "url" not in rows[0]


def test_source_allowlist_rejects_unknown_or_private_adapter():
    for name in ("shell", "../secret", "private_database"):
        try:
            sources.make_source(name)
        except ValueError:
            pass
        else:
            raise AssertionError("unallowlisted source was accepted")
