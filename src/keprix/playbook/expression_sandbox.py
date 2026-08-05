"""Restricted expression evaluation for playbook conditions and templates."""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

_log = logging.getLogger(__name__)

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")

_BOOL_NAMES = frozenset({"true", "false", "null", "True", "False", "None"})
_ROOT_NAMES = frozenset({"steps", "state", *_BOOL_NAMES})

_ALLOWED_BINOPS = (
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
)

_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_UNARY_OPS = (ast.Not, ast.USub)


class ExpressionError(ValueError):
    """User-supplied expression or template path is not allowed."""


def build_expression_context(state: dict[str, Any]) -> dict[str, Any]:
    """Build ``steps`` / ``state`` views from flat playbook run state."""
    steps: dict[str, Any] = {}
    nested = state.get("steps")
    if isinstance(nested, dict):
        for step_id, payload in nested.items():
            if isinstance(payload, dict):
                steps[str(step_id)] = dict(payload)
            else:
                steps[str(step_id)] = {"output": payload}

    for key, value in state.items():
        if key.endswith("_output"):
            step_id = key[: -len("_output")]
            entry = steps.setdefault(step_id, {})
            if isinstance(entry, dict):
                entry["output"] = value
            else:
                steps[step_id] = {"output": value}

    public_state = {
        key: value
        for key, value in state.items()
        if not key.startswith("_") and not key.endswith("_branch") and key != "steps"
    }
    return {"steps": steps, "state": public_state}


def evaluate_condition(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a boolean playbook condition without calling ``eval()``."""
    expr = (expression or "").strip()
    if not expr:
        raise ExpressionError("empty expression")
    if expr.startswith("#"):
        raise ExpressionError("expression is a comment placeholder; edit before running")

    tree = _parse_expression(expr)
    result = _eval_node(tree.body, context)
    if not isinstance(result, bool):
        raise ExpressionError(f"condition must be boolean, got {type(result).__name__}")
    return result


def render_template(template: str, context: dict[str, Any]) -> str:
    """Replace ``{{ steps.id.output }}`` / ``{{ state.key }}`` placeholders."""
    if not template:
        return template

    def _replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        try:
            value = resolve_path(path, context)
        except ExpressionError as exc:
            _log.warning("playbook template token %r skipped: %s", path, exc)
            return ""
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return str(value)
        return str(value)

    return _TEMPLATE_PATTERN.sub(_replace, template)


def resolve_path(path: str, context: dict[str, Any]) -> Any:
    """Resolve ``steps.foo.output.bar`` or ``state.key`` from *context*."""
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ExpressionError("empty template path")
    if parts[0] not in {"steps", "state"}:
        raise ExpressionError(f"template path must start with steps or state, got {parts[0]!r}")
    current: Any = context.get(parts[0])
    if current is None:
        return None
    for part in parts[1:]:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            raise ExpressionError(f"cannot traverse {part!r} on {type(current).__name__}")
    return current


def _parse_expression(expression: str) -> ast.Expression:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"invalid syntax: {exc.msg}") from exc
    if not isinstance(tree, ast.Expression):
        raise ExpressionError("expected eval expression")
    _validate_node(tree.body)
    return tree


def _validate_node(node: ast.AST) -> None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (bool, int, float, str)) or node.value is None:
            return
        raise ExpressionError(f"unsupported literal type {type(node.value).__name__}")

    if isinstance(node, ast.Name):
        if node.id in _ROOT_NAMES:
            return
        raise ExpressionError(f"unknown name {node.id!r}")

    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _ALLOWED_UNARY_OPS:
            raise ExpressionError(f"unsupported unary operator {type(node.op).__name__}")
        _validate_node(node.operand)
        return

    if isinstance(node, ast.BoolOp):
        if type(node.op) not in _ALLOWED_BOOL_OPS:
            raise ExpressionError(f"unsupported boolean operator {type(node.op).__name__}")
        for value in node.values:
            _validate_node(value)
        return

    if isinstance(node, ast.Compare):
        _validate_node(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in _ALLOWED_BINOPS:
                raise ExpressionError(f"unsupported comparison {type(op).__name__}")
            _validate_node(comparator)
        return

    if isinstance(node, ast.Attribute):
        _validate_path_root(node)
        return

    if isinstance(node, ast.Subscript):
        _validate_node(node.value)
        if isinstance(node.slice, ast.Constant):
            if isinstance(node.slice.value, (str, int)):
                return
            raise ExpressionError("subscript must be string or int literal")
        raise ExpressionError("dynamic subscripts are not allowed")

    if isinstance(node, ast.List):
        for element in node.elts:
            _validate_node(element)
        return

    if isinstance(node, ast.Tuple):
        for element in node.elts:
            _validate_node(element)
        return

    forbidden = (
        ast.Call,
        ast.Lambda,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.NamedExpr,
        ast.IfExp,
        ast.JoinedStr,
        ast.FormattedValue,
        ast.Dict,
        ast.Set,
        ast.Starred,
    )
    if isinstance(node, forbidden):
        raise ExpressionError(f"unsupported expression node {type(node).__name__}")
    raise ExpressionError(f"unsupported expression node {type(node).__name__}")


def _validate_path_root(node: ast.Attribute) -> None:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name) and current.id in {"steps", "state"}:
        parts.reverse()
        if current.id == "steps":
            if len(parts) < 2:
                raise ExpressionError("steps path must include step id and output")
            if parts[1] != "output":
                raise ExpressionError("steps path must use steps.<id>.output")
        return
    raise ExpressionError("attribute access is only allowed on steps or state")


def _eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id in {"true", "True"}:
            return True
        if node.id in {"false", "False"}:
            return False
        if node.id in {"null", "None"}:
            return None
        if node.id in {"steps", "state"}:
            return context.get(node.id)
        raise ExpressionError(f"unknown name {node.id!r}")

    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, context)
        if isinstance(node.op, ast.Not):
            return not bool(value)
        if isinstance(node.op, ast.USub):
            if not isinstance(value, (int, float)):
                raise ExpressionError("unary minus requires a number")
            return -value
        raise ExpressionError(f"unsupported unary operator {type(node.op).__name__}")

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            for value_node in node.values:
                if not _eval_node(value_node, context):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for value_node in node.values:
                if _eval_node(value_node, context):
                    return True
            return False
        raise ExpressionError(f"unsupported boolean operator {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for op, comparator_node in zip(node.ops, node.comparators):
            right = _eval_node(comparator_node, context)
            if isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.GtE):
                result = left >= right
            elif isinstance(op, ast.In):
                result = left in right
            elif isinstance(op, ast.NotIn):
                result = left not in right
            else:
                raise ExpressionError(f"unsupported comparison {type(op).__name__}")
            if not result:
                return False
            left = right
        return True

    if isinstance(node, ast.Attribute):
        return resolve_path(_attribute_path(node), context)

    if isinstance(node, ast.Subscript):
        return resolve_path(_attribute_path(node.value), context)

    if isinstance(node, ast.List):
        return [_eval_node(element, context) for element in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(element, context) for element in node.elts)

    raise ExpressionError(f"unsupported expression node {type(node).__name__}")


def _attribute_path(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return ".".join(parts)
    raise ExpressionError("invalid attribute path")
