"""PSPP procedure definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProcedureSpec:
    name: str
    syntax_keyword: str
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()


PROCEDURES: dict[str, ProcedureSpec] = {
    "frequencies": ProcedureSpec("frequencies", "FREQUENCIES", ("variables",)),
    "descriptives": ProcedureSpec("descriptives", "DESCRIPTIVES", ("variables",)),
    "crosstabs": ProcedureSpec("crosstabs", "CROSSTABS", ("row", "column")),
    "t_test": ProcedureSpec("t_test", "T-TEST", ("groups", "dependent")),
    "oneway": ProcedureSpec("oneway", "ONEWAY", ("dependent", "factor")),
    "correlations": ProcedureSpec("correlations", "CORRELATIONS", ("variables",)),
    "regression": ProcedureSpec("regression", "REGRESSION", ("dependent", "independents")),
    "logistic_regression": ProcedureSpec(
        "logistic_regression",
        "LOGISTIC REGRESSION",
        ("dependent", "independents"),
    ),
}


def normalize_procedure(payload: dict[str, Any]) -> tuple[ProcedureSpec, dict[str, Any]]:
    name = str(payload.get("type") or payload.get("procedure") or "").lower()
    if name not in PROCEDURES:
        raise ValueError(f"Unsupported PSPP procedure: {name}")
    spec = PROCEDURES[name]
    params = dict(payload.get("params") or payload)
    params.pop("type", None)
    params.pop("procedure", None)
    for required in spec.required_params:
        if required not in params:
            raise ValueError(f"Procedure `{name}` requires `{required}`")
    return spec, params
