from __future__ import annotations

import ast
import importlib
from pathlib import Path


TUI_ROOT = Path("src/keprix/tui")
REQUIRED_PACKAGES = (
    "commands",
    "composer",
    "contracts",
    "gateway",
    "layout",
    "overlays",
    "panels",
    "renderer",
    "runtime",
    "search",
    "sessions",
    "terminal",
    "widgets",
)


def test_required_tui_subpackages_exist() -> None:
    missing = [name for name in REQUIRED_PACKAGES if not (TUI_ROOT / name / "__init__.py").exists()]
    assert missing == []


def test_required_split_modules_exist() -> None:
    required = {
        "commands": ("schema.py", "registry.py", "completion.py", "preview.py", "args.py", "dispatch.py", "history.py", "fuzzy.py"),
        "composer": ("history.py", "queue.py", "paste.py", "metrics.py", "external_editor.py", "voice.py", "busy_modes.py"),
        "renderer": ("cells.py", "measure.py", "diff.py", "markdown.py", "code_blocks.py", "messages.py", "selection.py", "viewport.py", "theme.py", "snapshots.py"),
        "runtime": ("events.py", "store.py", "adapters.py", "details.py", "tools.py", "subagents.py", "messages.py", "api_inspector.py"),
        "panels": ("details.py", "sessions.py", "queue.py", "skills.py", "plugins.py", "model_picker.py", "debug.py", "help.py"),
        "overlays": ("approval.py", "clarify.py", "setup.py", "pager.py"),
        "terminal": ("capabilities.py", "startup.py", "modes.py", "raw.py", "title.py", "notifications.py", "clipboard.py", "platform.py", "resize.py", "links.py"),
    }
    missing: list[str] = []
    for package, files in required.items():
        missing.extend(str(TUI_ROOT / package / file_name) for file_name in files if not (TUI_ROOT / package / file_name).exists())
    assert missing == []


def test_new_subpackages_import_cleanly() -> None:
    for name in REQUIRED_PACKAGES:
        importlib.import_module(f"keprix.tui.{name}")


def test_tui_core_does_not_import_product_modules_directly() -> None:
    forbidden_prefixes = (
        "keprix.agent_os",
        "keprix.billing",
        "keprix.channel_shield",
        "keprix.ops",
        "keprix.scout",
        "keprix.web",
    )
    offenders: list[str] = []
    for path in TUI_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if module.startswith(forbidden_prefixes):
                        offenders.append(f"{path}:{module}")
                continue
            if module.startswith(forbidden_prefixes):
                offenders.append(f"{path}:{module}")
    assert offenders == []


def test_granularity_has_contract_tests() -> None:
    required_tests = (
        "tests/tui/test_granularity_contract.py",
        "tests/tui/test_import_compatibility.py",
        "tests/tui/test_renderer_contracts.py",
        "tests/tui/test_command_contracts.py",
        "tests/tui/test_runtime_contracts.py",
    )
    assert [path for path in required_tests if not Path(path).exists()] == []
