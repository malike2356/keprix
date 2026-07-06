"""Missing value tests."""

from __future__ import annotations

from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.datasets.missing_values import apply_missing_codes, normalize_missing


def test_normalize_default_missing_codes():
    assert normalize_missing("NA") is None
    assert normalize_missing("-99") is None
    assert normalize_missing("42") == "42"


def test_apply_missing_codes_to_rows():
    codebook = Codebook(
        dataset_id="ds-1",
        version_id="ds-1-v1",
        variables=[
            VariableDefinition(name="score", missing_codes=["88", "99"]),
            VariableDefinition(name="region"),
        ],
    )
    rows = [{"score": "88", "region": "north"}, {"score": "70", "region": "south"}]
    cleaned = apply_missing_codes(rows, codebook)
    assert cleaned[0]["score"] is None
    assert cleaned[1]["score"] == "70"
