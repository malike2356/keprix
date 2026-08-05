from __future__ import annotations

import importlib


def test_existing_flat_imports_remain_compatible() -> None:
    modules = (
        "keprix.tui.composer",
        "keprix.tui.slash_registry",
        "keprix.tui.slash_commands",
        "keprix.tui.slash_handler",
        "keprix.tui.slash_arg_parser",
        "keprix.tui.runtime_events",
        "keprix.tui.runtime_store",
        "keprix.tui.details_runtime",
    )
    for module in modules:
        importlib.import_module(module)


def test_composer_package_exports_old_symbols() -> None:
    composer = importlib.import_module("keprix.tui.composer")
    queue = composer.MessageQueue()
    queue.enqueue("hello")
    assert queue.pop() == "hello"
    history = composer.InputHistory(max_items=2)
    history.push("one")
    history.push("two")
    assert history.previous() == "two"


def test_new_package_imports_are_stable() -> None:
    modules = (
        "keprix.tui.commands.registry",
        "keprix.tui.commands.dispatch",
        "keprix.tui.composer.queue",
        "keprix.tui.renderer.messages",
        "keprix.tui.runtime.store",
        "keprix.tui.panels.queue",
        "keprix.tui.overlays.approval",
        "keprix.tui.terminal.capabilities",
        "keprix.tui.gateway.types",
        "keprix.tui.contracts.parity",
    )
    for module in modules:
        importlib.import_module(module)
