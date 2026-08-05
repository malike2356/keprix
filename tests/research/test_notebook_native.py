"""Prompt 268 native Quick Notebook tests."""

from __future__ import annotations

from keprix.research.notebook_native import NotebookNativeEngine, normalize_notebook_source


def test_native_notebook_report_uses_two_text_sources() -> None:
    sources = [
        normalize_notebook_source(
            {
                "kind": "text",
                "title": "Alpha notes",
                "ref": "Alpha retention improved after onboarding checklists were added.",
            }
        ),
        normalize_notebook_source(
            {
                "kind": "text",
                "title": "Beta notes",
                "ref": "Beta activation increased when source-grounded reports included citations.",
            }
        ),
    ]

    result = NotebookNativeEngine().run(query="How did onboarding affect retention and activation?", sources=sources)

    assert "[S1]" in result["report_md"]
    assert "[S2]" in result["report_md"]
    assert len(result["citations"]) == 2
    assert result["citations"][0]["title"] == "Alpha notes"


def test_native_notebook_requires_two_sources() -> None:
    sources = [normalize_notebook_source({"kind": "text", "ref": "Only one source."})]

    try:
        NotebookNativeEngine().run(query="What happened?", sources=sources)
    except ValueError as exc:
        assert "at least two sources" in str(exc)
    else:
        raise AssertionError("expected ValueError")
