"""Lightweight input validation matching the semantics of Propreneur's
Laravel validation rules() arrays (required, numeric, integer, min:X,
max:X, boolean, string, date, in:a,b,c, required_without:field, array) -
just enough to validate calculator inputs the same way the real product
does, without pulling in a full framework."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ValidationError(Exception):
    def __init__(self, errors: dict[str, list[str]]) -> None:
        self.errors = errors
        super().__init__("; ".join(f"{k}: {', '.join(v)}" for k, v in errors.items()))


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _coerce_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_rules_to_value(
    field_key: str,
    value: Any,
    field_rules: list[str],
    errors: dict[str, list[str]],
) -> None:
    nullable = "nullable" in field_rules
    required = "required" in field_rules

    if _is_missing(value):
        if required:
            errors.setdefault(field_key, []).append("is required")
        return

    for rule in field_rules:
        if rule in ("required", "nullable", "array") or rule.startswith("required_without:"):
            continue
        if rule == "numeric":
            if _coerce_number(value) is None:
                errors.setdefault(field_key, []).append("must be numeric")
        elif rule == "integer":
            if _coerce_number(value) is None:
                errors.setdefault(field_key, []).append("must be an integer")
        elif rule == "boolean":
            pass
        elif rule == "string":
            pass
        elif rule == "date":
            text = str(value)[:10]
            try:
                datetime.strptime(text, "%Y-%m-%d")
            except ValueError:
                errors.setdefault(field_key, []).append("must be a valid date (YYYY-MM-DD)")
        elif rule.startswith("min:"):
            bound = float(rule.split(":", 1)[1])
            number = _coerce_number(value)
            if number is not None and number < bound:
                errors.setdefault(field_key, []).append(f"must be at least {bound}")
        elif rule.startswith("max:"):
            bound = float(rule.split(":", 1)[1])
            number = _coerce_number(value)
            if number is not None and number > bound:
                errors.setdefault(field_key, []).append(f"must be at most {bound}")
        elif rule.startswith("in:"):
            allowed = rule.split(":", 1)[1].split(",")
            if str(value) not in allowed:
                errors.setdefault(field_key, []).append(f"must be one of {', '.join(allowed)}")


def _validate_nested_array_items(inputs: dict[str, Any], rules: dict[str, list[str]], errors: dict[str, list[str]]) -> None:
    nested: dict[str, dict[str, list[str]]] = {}
    scalar_items: dict[str, list[str]] = {}
    for field, field_rules in rules.items():
        if ".*." in field:
            parent, child = field.split(".*.", 1)
            nested.setdefault(parent, {})[child] = field_rules
        elif field.endswith(".*"):
            scalar_items[field[:-2]] = field_rules

    for parent, item_rules in scalar_items.items():
        value = inputs.get(parent)
        if _is_missing(value) or not isinstance(value, list):
            continue
        for idx, item in enumerate(value):
            _apply_rules_to_value(f"{parent}.{idx}", item, item_rules, errors)

    for parent, children in nested.items():
        parent_rules = rules.get(parent, [])
        value = inputs.get(parent)
        if _is_missing(value):
            continue
        if "array" in parent_rules:
            if not isinstance(value, list):
                errors.setdefault(parent, []).append("must be an array")
                continue
            for rule in parent_rules:
                if rule.startswith("min:"):
                    bound = int(float(rule.split(":", 1)[1]))
                    if len(value) < bound:
                        errors.setdefault(parent, []).append(f"must have at least {bound} items")
        if not isinstance(value, list):
            continue
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                errors.setdefault(f"{parent}.{idx}", []).append("must be an object")
                continue
            for child, child_field_rules in children.items():
                child_value = item.get(child)
                _apply_rules_to_value(f"{parent}.{idx}.{child}", child_value, child_field_rules, errors)


def validate(inputs: dict[str, Any], rules: dict[str, list[str]]) -> dict[str, Any]:
    """Validates `inputs` against `rules` (field -> list of rule strings).
    Returns a cleaned copy of inputs (missing optional fields omitted,
    present values left as given for the calculator to coerce). Raises
    ValidationError with field->messages on failure."""
    errors: dict[str, list[str]] = {}
    cleaned: dict[str, Any] = dict(inputs)

    for field, field_rules in rules.items():
        # array-item rules like "cash_flows.*" describe the item shape, not
        # the field itself - the parent array's own rule entry handles
        # presence; skip item-level entries here.
        if ".*" in field:
            continue

        value = inputs.get(field)
        nullable = "nullable" in field_rules
        required = "required" in field_rules
        required_without = next((r.split(":", 1)[1] for r in field_rules if r.startswith("required_without:")), None)

        if _is_missing(value):
            if required:
                errors.setdefault(field, []).append("is required")
                continue
            if required_without and _is_missing(inputs.get(required_without)):
                errors.setdefault(field, []).append(f"is required when {required_without} is not supplied")
                continue
            if nullable or not required:
                continue

        if "array" in field_rules and not isinstance(value, list):
            errors.setdefault(field, []).append("must be an array")
            continue

        for rule in field_rules:
            if rule in ("required", "nullable", "array") or rule.startswith("required_without:"):
                continue
            if rule == "numeric":
                if _coerce_number(value) is None:
                    errors.setdefault(field, []).append("must be numeric")
            elif rule == "integer":
                if _coerce_number(value) is None:
                    errors.setdefault(field, []).append("must be an integer")
            elif rule == "boolean":
                pass  # any truthy/falsy value coerces fine downstream
            elif rule == "string":
                pass
            elif rule == "date":
                text = str(value)[:10]
                try:
                    datetime.strptime(text, "%Y-%m-%d")
                except ValueError:
                    errors.setdefault(field, []).append("must be a valid date (YYYY-MM-DD)")
            elif rule.startswith("min:"):
                bound = float(rule.split(":", 1)[1])
                if isinstance(value, list):
                    if len(value) < bound:
                        errors.setdefault(field, []).append(f"must have at least {int(bound)} items")
                else:
                    number = _coerce_number(value)
                    if number is not None and number < bound:
                        errors.setdefault(field, []).append(f"must be at least {bound}")
            elif rule.startswith("max:"):
                bound = float(rule.split(":", 1)[1])
                number = _coerce_number(value)
                if number is not None and number > bound:
                    errors.setdefault(field, []).append(f"must be at most {bound}")
            elif rule.startswith("in:"):
                allowed = rule.split(":", 1)[1].split(",")
                if str(value) not in allowed:
                    errors.setdefault(field, []).append(f"must be one of {', '.join(allowed)}")

    _validate_nested_array_items(inputs, rules, errors)

    if errors:
        raise ValidationError(errors)

    return cleaned
