"""Infer JSON Schema from generated tool Python source (Prompt 150)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InferredSchema:
    name: str
    description: str
    input_schema: dict[str, Any]
    errors: list[str] = field(default_factory=list)


_TYPE_MAP: dict[str, dict[str, str]] = {
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "bool": {"type": "boolean"},
    "list": {"type": "array"},
    "dict": {"type": "object"},
    "List": {"type": "array"},
    "Dict": {"type": "object"},
}


def infer_schema(source_code: str, function_name: str) -> InferredSchema:
    """Parse source with ast only; never exec or import the module."""
    errors: list[str] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return InferredSchema(
            name=function_name,
            description="",
            input_schema={},
            errors=[f"syntax error: {exc.msg}"],
        )

    func = _find_function(tree, function_name)
    if func is None:
        return InferredSchema(
            name=function_name,
            description="",
            input_schema={},
            errors=[f"function not found: {function_name}"],
        )

    description = _function_description(func)
    properties: dict[str, Any] = {}
    required: list[str] = []
    param_docs = _parse_param_docs(ast.get_docstring(func) or "")

    for arg in func.args.args:
        if arg.arg in {"self", "cls", "kwargs"}:
            continue
        if arg.arg == "args" and len(func.args.args) == 1:
            properties = {"type": "object", "properties": {}, "additionalProperties": True}
            break
        schema, optional = _annotation_schema(arg.annotation)
        if arg.arg in param_docs:
            schema = dict(schema)
            schema["description"] = param_docs[arg.arg]
        properties[arg.arg] = schema
        if not optional and arg.arg != "kwargs":
            required.append(arg.arg)

    if isinstance(properties, dict) and properties.get("type") == "object":
        input_schema = properties
    else:
        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    if not properties and not errors:
        errors.append("no inferrable parameters")

    return InferredSchema(
        name=function_name,
        description=description,
        input_schema=input_schema,
        errors=errors,
    )


def infer_handler_schema(source_code: str, tool_name: str) -> InferredSchema:
    """Infer schema from a conventional Keprix handler name."""
    candidates = [
        f"{tool_name}_handler",
        f"handle_{tool_name}",
        "handler",
    ]
    for name in candidates:
        result = infer_schema(source_code, name)
        if not result.errors:
            return result
    return infer_schema(source_code, candidates[0])


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _function_description(func: ast.FunctionDef) -> str:
    doc = ast.get_docstring(func) or ""
    lines = []
    for line in doc.splitlines():
        stripped = line.strip()
        if not stripped:
            break
        if stripped.lower().startswith("args:"):
            break
        lines.append(stripped)
    return " ".join(lines).strip()


def _parse_param_docs(docstring: str) -> dict[str, str]:
    docs: dict[str, str] = {}
    if not docstring:
        return docs
    in_args = False
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower() in {"args:", "arguments:"}:
            in_args = True
            continue
        if in_args:
            if stripped.lower().startswith(("returns:", "raises:", "yields:")):
                break
            match = re.match(r"^(\w+)\s*:\s*(.+)$", stripped)
            if match:
                docs[match.group(1)] = match.group(2).strip()
    return docs


def _annotation_schema(annotation: ast.expr | None) -> tuple[dict[str, Any], bool]:
    if annotation is None:
        return {}, False

    if isinstance(annotation, ast.Name):
        return dict(_TYPE_MAP.get(annotation.id, {})), False

    if isinstance(annotation, ast.Constant) and annotation.value is None:
        return {}, True

    if isinstance(annotation, ast.Subscript):
        origin = annotation.value
        if isinstance(origin, ast.Name) and origin.id in {"Optional", "Union"}:
            inner = annotation.slice
            if isinstance(inner, ast.Tuple) and inner.elts:
                inner = inner.elts[0]
            schema, _ = _annotation_schema(inner)
            return schema, True
        if isinstance(origin, ast.Name) and origin.id in {"list", "List"}:
            return {"type": "array"}, False
        if isinstance(origin, ast.Name) and origin.id in {"dict", "Dict"}:
            return {"type": "object"}, False

    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left_schema, left_optional = _annotation_schema(annotation.left)
        right_schema, right_optional = _annotation_schema(annotation.right)
        if right_schema == {} and isinstance(annotation.right, ast.Constant) and annotation.right.value is None:
            return left_schema, True
        if left_schema == {} and isinstance(annotation.left, ast.Constant) and annotation.left.value is None:
            return right_schema, True
        return left_schema or right_schema, left_optional or right_optional

    if isinstance(annotation, ast.Attribute) and isinstance(annotation.value, ast.Name):
        if annotation.value.id == "typing" and annotation.attr in _TYPE_MAP:
            return dict(_TYPE_MAP[annotation.attr]), False

    return {}, False
