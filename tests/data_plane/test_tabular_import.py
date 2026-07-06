"""Tests for Excel and SPSS tabular import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.data_architecture.research_plane import import_dataset_file
from keprix.data_plane.tabular_import import (
    _excel_available,
    _spss_available,
    import_excel_dataset,
    import_spss_dataset,
    supported_tabular_suffixes,
)


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    path = tmp_path / "survey.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Responses"
    sheet.append(["age", "score"])
    sheet.append([25, 91])
    sheet.append([31, 84])
    workbook.save(path)
    return path


@pytest.fixture
def sample_sav(tmp_path: Path) -> Path:
    pytest.importorskip("pyreadstat")
    import pandas as pd
    import pyreadstat

    path = tmp_path / "survey.sav"
    frame = pd.DataFrame({"age": [25, 31], "satisfaction": [1, 2]})
    variable_labels = {"age": "Respondent age", "satisfaction": "Satisfaction score"}
    value_labels = {"satisfaction": {1: "Low", 2: "High"}}
    pyreadstat.write_sav(
        frame,
        str(path),
        column_labels=variable_labels,
        variable_value_labels=value_labels,
    )
    return path


def test_supported_formats_include_excel_and_spss_when_libraries_present() -> None:
    formats = supported_tabular_suffixes()
    assert ".csv" in formats
    if _excel_available():
        assert ".xlsx" in formats
    if _spss_available():
        assert ".sav" in formats


@pytest.mark.skipif(not _excel_available(), reason="openpyxl not installed")
def test_excel_import_creates_queryable_dataset(sample_xlsx: Path) -> None:
    meta = import_excel_dataset(sample_xlsx)
    assert meta["row_count"] == 2
    assert meta["source_format"] == "excel"
    assert meta["sheet"] == "Responses"
    assert Path(meta["metadata_path"]).exists()


@pytest.mark.skipif(not _spss_available(), reason="pyreadstat not installed")
def test_spss_import_preserves_labels(sample_sav: Path) -> None:
    meta = import_spss_dataset(sample_sav)
    assert meta["row_count"] == 2
    assert meta["source_format"] == "spss"
    assert meta["variable_labels"]["age"] == "Respondent age"
    assert meta["value_labels"]["satisfaction"]["1.0"] == "Low"
    payload = json.loads(Path(meta["metadata_path"]).read_text(encoding="utf-8"))
    assert payload["variable_labels"]["satisfaction"] == "Satisfaction score"


@pytest.mark.skipif(not _excel_available(), reason="openpyxl not installed")
def test_research_plane_routes_excel(sample_xlsx: Path) -> None:
    meta = import_dataset_file(sample_xlsx)
    assert meta["source_format"] == "excel"


@pytest.mark.skipif(not _spss_available(), reason="pyreadstat not installed")
def test_research_plane_routes_spss(sample_sav: Path) -> None:
    meta = import_dataset_file(sample_sav)
    assert meta["source_format"] == "spss"


def test_missing_spss_library_raises_clean_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "empty.sav"
    path.write_bytes(b"not a real sav")
    monkeypatch.setattr("keprix.data_plane.tabular_import._spss_available", lambda: False)
    with pytest.raises(ImportError, match="pyreadstat"):
        import_spss_dataset(path)
