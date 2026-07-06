"""Hardened AST analysis for generated tool code."""

from __future__ import annotations

import ast

BLOCKED_IMPORTS: frozenset[str] = frozenset({
    "importlib",
    "importlib.util",
    "importlib.machinery",
    "importlib.abc",
    "__import__",
    "builtins",
    "__builtins__",
    "ctypes",
    "cffi",
    "cython",
    "socket",
    "ssl",
    "asyncio.selector_events",
    "asyncio.proactor_events",
    "_ssl",
    "_socket",
    "subprocess",
    "multiprocessing",
    "threading",
    "concurrent.futures",
    "asyncio.subprocess",
    "_thread",
    "struct",
    "mmap",
    "array",
    "pickle",
    "shelve",
    "marshal",
    "code",
    "codeop",
    "compileall",
    "dis",
    "py_compile",
})

BLOCKED_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
    "vars",
    "locals",
    "globals",
    "dir",
    "type",
    "memoryview",
})

BLOCKED_ATTRIBUTES: frozenset[str] = frozenset({
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__init_subclass__",
    "__dict__",
    "__code__",
    "__globals__",
    "__builtins__",
    "__loader__",
    "__spec__",
    "f_locals",
    "f_globals",
    "f_builtins",
    "gi_frame",
    "cr_frame",
})


class AstAnalyser(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in BLOCKED_IMPORTS or any(alias.name.startswith(f"{blocked}.") for blocked in BLOCKED_IMPORTS):
                self.violations.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module in BLOCKED_IMPORTS or any(module.startswith(f"{blocked}.") for blocked in BLOCKED_IMPORTS):
            self.violations.append(f"Blocked import from: {module}")
        for alias in node.names:
            if alias.name in BLOCKED_CALLS:
                self.violations.append(f"Blocked import of: {alias.name} from {module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            self.violations.append(f"Blocked call: {node.func.id}()")
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {"Popen", "call", "run", "check_output", "check_call"}:
                self.violations.append(f"Blocked call: .{node.func.attr}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BLOCKED_ATTRIBUTES:
            self.violations.append(f"Blocked attribute access: .{node.attr}")
        self.generic_visit(node)


def analyse(source_code: str) -> list[str]:
    """Return list of violations. Empty list means safe."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return [f"SyntaxError: {exc}"]
    analyser = AstAnalyser()
    analyser.visit(tree)
    return analyser.violations
