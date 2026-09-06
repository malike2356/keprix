"""Workspace-aware calculator service and override persistence."""

from __future__ import annotations

import json
from typing import Any

from keprix.property_data.refresh import _connection, now
from keprix.property_data.schema import ensure_schema

from .constants import ConfigResolver
from .registry import CalculatorError, list_strategies, rules_for, run_calculator


def calculator_settings(workspace_id: str, *, connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT overrides_json,updated_at FROM property_calculator_settings WHERE workspace_id=?", (workspace_id,)).fetchone()
    return {"workspace_id": workspace_id, "overrides": json.loads(row[0] or "{}") if row else {}, "updated_at": row[1] if row else ""}


def update_calculator_settings(workspace_id: str, overrides: dict[str, Any], *, connection=None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in overrides.items():
        if isinstance(value, (int, float)) and value < 0:
            raise CalculatorError(f"override {key} must not be negative")
        if "ltv" in str(key).lower() and isinstance(value, (int, float)) and not 0 <= value <= 100:
            raise CalculatorError(f"override {key} must be between 0 and 100")
        if key == "sdlt_residential_bands":
            if not isinstance(value, list) or any(not isinstance(band, dict) or float(band.get("rate", -1)) < 0 for band in value):
                raise CalculatorError("sdlt_residential_bands must be a list of non-negative rate bands")
        clean[str(key)] = value
    connection = _connection(connection)
    ensure_schema(connection)
    connection.execute("INSERT INTO property_calculator_settings (workspace_id,overrides_json,updated_at) VALUES (?,?,?) ON CONFLICT(workspace_id) DO UPDATE SET overrides_json=excluded.overrides_json,updated_at=excluded.updated_at", (workspace_id, json.dumps(clean), now()))
    connection.commit()
    return calculator_settings(workspace_id, connection=connection)


def run_workspace_calculator(workspace_id: str, strategy: str, inputs: dict[str, Any], *, connection=None) -> dict[str, Any]:
    settings = calculator_settings(workspace_id, connection=connection)
    result = run_calculator(strategy, inputs, ConfigResolver(settings["overrides"]))
    return {"strategy": strategy, "inputs": inputs, "result": result, "workspace_id": workspace_id}


def calculator_rules(strategy: str, workspace_id: str, *, connection=None) -> dict[str, Any]:
    return {"strategy": strategy, "workspace_id": workspace_id, "rules": rules_for(strategy), "overrides": calculator_settings(workspace_id, connection=connection)["overrides"]}
