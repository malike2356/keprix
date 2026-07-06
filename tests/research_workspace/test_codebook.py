"""Codebook tests."""

from __future__ import annotations

from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.datasets.variables import build_variables_from_columns


def test_codebook_variable_roundtrip():
    variable = VariableDefinition(
        name="age",
        label="Respondent age",
        var_type="numeric",
        measurement_level="scale",
        value_labels={"1": "Young", "2": "Old"},
        missing_codes=["-99"],
        validation_rules=["min:0", "max:120"],
        notes="Years",
    )
    codebook = Codebook(dataset_id="ds-1", version_id="ds-1-v1", variables=[variable])
    restored = Codebook.from_dict(codebook.to_dict())
    assert restored.get_variable("age").label == "Respondent age"
    assert restored.get_variable("age").missing_codes == ["-99"]


def test_infer_variables_from_sample_rows():
    rows = [{"age": "30", "region": "north"}, {"age": "25", "region": "south"}]
    variables = build_variables_from_columns(["age", "region"], rows, labels={"age": "Age"})
    age = next(variable for variable in variables if variable.name == "age")
    region = next(variable for variable in variables if variable.name == "region")
    assert age.label == "Age"
    assert age.var_type == "numeric"
    assert region.measurement_level == "ordinal"
