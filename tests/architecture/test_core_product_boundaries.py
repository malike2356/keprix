from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "keprix"

CORE_PREFIXES = (
    "keprix.agent",
    "keprix.tui",
    "keprix.tools",
    "keprix.memory",
    "keprix.config",
    "keprix.cli",
    "keprix.__main__",
)

PRODUCT_PREFIXES = (
    "keprix.agent_os",
    "keprix.channel_shield",
    "keprix.billing",
    "keprix.agent_apps",
    "keprix.backend",
    "keprix.ops",
    "keprix.scout",
)

@dataclass(frozen=True)
class ImportViolation:
    module: str
    path: Path
    line: int
    imported: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.module, self.imported)

    def format(self) -> str:
        rel = self.path.relative_to(ROOT)
        return f"{rel}:{self.line}: {self.module} imports product module {self.imported}"


def _under(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


def _module_name(path: Path) -> str:
    rel = path.relative_to(SRC).with_suffix("")
    return ".".join(rel.parts)


def _resolve_relative_import(module_name: str, level: int, imported: str | None) -> str | None:
    if level <= 0:
        return imported
    parts = module_name.split(".")
    if level > len(parts):
        return imported
    base = parts[: len(parts) - level]
    if imported:
        base.append(imported)
    return ".".join(base) if base else imported


def _imported_modules(module_name: str, tree: ast.AST) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported = _resolve_relative_import(module_name, node.level, node.module)
            if imported:
                imports.append((node.lineno, imported))
    return imports


def _core_python_files() -> list[Path]:
    files: list[Path] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        module = _module_name(path)
        if _under(module, CORE_PREFIXES):
            files.append(path)
    return files


def _direct_product_imports() -> list[ImportViolation]:
    violations: list[ImportViolation] = []
    for path in _core_python_files():
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, imported in _imported_modules(module, tree):
            if _under(imported, PRODUCT_PREFIXES):
                violations.append(
                    ImportViolation(
                        module=module,
                        path=path,
                        line=line,
                        imported=imported,
                    )
                )
    return violations


def test_core_modules_do_not_import_product_modules_directly() -> None:
    violations = _direct_product_imports()
    assert not violations, "\n".join(
        [
            "Core modules must use product registries, hooks, or adapters instead of direct product imports.",
            *[violation.format() for violation in violations],
        ]
    )


def test_tui_does_not_import_product_modules() -> None:
    violations = [
        violation
        for violation in _direct_product_imports()
        if violation.module == "keprix.tui" or violation.module.startswith("keprix.tui.")
    ]
    assert not violations, "\n".join(violation.format() for violation in violations)
