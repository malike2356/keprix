"""BibTeX and Better BibTeX import tests."""

from __future__ import annotations

from keprix.research_workspace.citations.better_bibtex import parse_better_bibtex
from keprix.research_workspace.citations.bibtex import parse_bibtex, record_to_bibtex
from keprix.research_workspace.citations.bibliography import export_bibliography
from keprix.research_workspace.citations.models import CitationRecord


BIBTEX_SAMPLE = """
@article{smith2023water,
  author = {Smith, John and Doe, Jane},
  title = {Water table trends},
  year = {2023},
  journal = {Hydro Review},
  doi = {10.1000/example}
}
"""

BBT_SAMPLE = """
@article{smith2023water,
  citationKey = {smith2023water},
  author = {Smith, John},
  title = {Water table trends},
  year = {2023},
  journal = {Hydro Review}
}
"""


def test_parse_bibtex_entry():
    records = parse_bibtex(BIBTEX_SAMPLE)
    assert len(records) == 1
    record = records[0]
    assert record.citation_key == "smith2023water"
    assert record.authors == ["Smith, John", "Doe, Jane"]
    assert record.year == "2023"
    assert record.doi == "10.1000/example"


def test_better_bibtex_preserves_stable_key():
    records = parse_better_bibtex(BBT_SAMPLE)
    assert records[0].citation_key == "smith2023water"
    assert records[0].source == "better_bibtex"


def test_bibliography_export_formats():
    record = CitationRecord(
        item_key="smith2023water",
        citation_key="smith2023water",
        title="Water table trends",
        authors=["Smith, John"],
        year="2023",
        publication="Hydro Review",
        doi="10.1000/example",
    )
    bibtex = export_bibliography([record], "bibtex")
    assert "@article{smith2023water" in bibtex
    markdown = export_bibliography([record], "markdown")
    assert "Smith, John" in markdown
    report = export_bibliography([record], "report")
    assert "## Bibliography" in report
    roundtrip = record_to_bibtex(record)
    assert "doi = {10.1000/example}" in roundtrip
