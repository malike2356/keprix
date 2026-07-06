"""PSPP syntax generation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.stats.pspp.errors import PSPPUnsafeFragmentError
from keprix.research_workspace.stats.pspp.syntax import generate_analysis_syntax, sanitize_identifier


def test_generate_syntax_from_codebook(tmp_path):
    codebook = Codebook(
        dataset_id="ds-1",
        version_id="ds-1-v1",
        variables=[
            VariableDefinition(
                name="age",
                label="Age",
                value_labels={"1": "Young"},
                missing_codes=["-99"],
            ),
            VariableDefinition(name="region", label="Region"),
        ],
    )
    data_path = tmp_path / "workspace" / "datasets" / "derived" / "ds-1" / "v1" / "data.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("age,region\n30,north\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    syntax = generate_analysis_syntax(
        codebook=codebook,
        data_path=data_path,
        workspace_root=workspace_root,
        procedures=[
            {"type": "frequencies", "variables": ["age", "region"]},
            {"type": "descriptives", "variables": ["age"]},
            {"type": "crosstabs", "row": "region", "column": "age"},
            {"type": "correlations", "variables": ["age"]},
            {"type": "regression", "dependent": "age", "independents": ["region"]},
        ],
    )
    assert "GET FILE=" in syntax
    assert "VARIABLE LABELS age 'Age'" in syntax
    assert "VALUE LABELS age 1 'Young'." in syntax
    assert "MISSING VALUES age (-99)." in syntax
    assert "FREQUENCIES VARIABLES=age region." in syntax
    assert "DESCRIPTIVES VARIABLES=age." in syntax
    assert "CROSSTABS /TABLES=region BY age." in syntax
    assert "REGRESSION /DEPENDENT=age /METHOD=ENTER region." in syntax


def test_reject_unsafe_identifiers():
    with pytest.raises(PSPPUnsafeFragmentError):
        sanitize_identifier("age;rm -rf")
