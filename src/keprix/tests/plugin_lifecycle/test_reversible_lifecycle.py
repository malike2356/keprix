"""Tests for reversible plugin lifecycle (prompt 769)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from keprix.plugin_lifecycle import (
    disable_plugin_hot,
    enable_plugin_hot,
    get_lifecycle_ledger,
    get_prompt_section,
    list_audit_events,
    list_prompt_sections,
    reset_lifecycle_for_tests,
)
from keprix.seams import ensure_default_seams, get_seam_registry, reset_seams_for_tests
from keprix_cli.plugins import PluginContext, PluginManager, PluginManifest
from tools.registry import registry as tool_registry


ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _fresh(tmp_path):
    reset_lifecycle_for_tests()
    reset_seams_for_tests(sandbox_root=tmp_path / "sb", memory_base=tmp_path / "mem")
    # Drop any leftover test tools
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("lifecycle_test_"):
            tool_registry.deregister(name)
    yield
    reset_lifecycle_for_tests()
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("lifecycle_test_"):
            tool_registry.deregister(name)


def _make_manager_and_ctx(plugin_id: str = "lifecycle-demo") -> tuple[PluginManager, PluginContext]:
    mgr = PluginManager()
    manifest = PluginManifest(
        name=plugin_id,
        key=plugin_id,
        source="user",
        kind="standalone",
    )
    mgr._plugins[plugin_id] = type(
        "LP",
        (),
        {"manifest": manifest, "enabled": True, "module": None},
    )()
    # Minimal LoadedPlugin-like object with mutable attrs used by unmount
    from keprix_cli.plugins import LoadedPlugin

    mgr._plugins[plugin_id] = LoadedPlugin(manifest=manifest, enabled=True)
    ctx = PluginContext(manifest, mgr)
    return mgr, ctx


def test_register_three_effects_unload_clears_all(tmp_path):
    mgr, ctx = _make_manager_and_ctx()
    plugin_id = "lifecycle-demo"

    def _handler(args, **kwargs):
        return '{"ok": true}'

    ctx.register_tool(
        name="lifecycle_test_alpha",
        toolset="lifecycle_test",
        schema={"name": "lifecycle_test_alpha", "description": "t", "parameters": {}},
        handler=_handler,
        description="t",
    )
    ctx.register_prompt_section("lifecycle.demo.banner", "BANNER_TEXT")
    ensure_default_seams()

    class DemoFs:
        provider_id = "fs.lifecycle_demo"

        def read_text(self, path: str, *, encoding: str = "utf-8") -> str:
            return "demo"

        def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None:
            return None

        def exists(self, path: str) -> bool:
            return False

        def list_dir(self, path: str = ".") -> list[str]:
            return []

        def tool_schemas(self):
            return []

    ctx.register_seam_provider("fs", DemoFs(), make_active=True)

    ledger = get_lifecycle_ledger().get(plugin_id)
    assert ledger is not None
    assert "lifecycle_test_alpha" in ledger.tools
    assert "lifecycle.demo.banner" in ledger.prompt_sections
    assert ("fs", "fs.lifecycle_demo") in ledger.seam_providers
    assert tool_registry.get_entry("lifecycle_test_alpha") is not None
    assert get_prompt_section("lifecycle.demo.banner") == "BANNER_TEXT"
    assert get_seam_registry().active_id("fs") == "fs.lifecycle_demo"

    result = mgr.unmount_plugin(plugin_id, who="test")
    assert result["ok"] is True
    assert tool_registry.get_entry("lifecycle_test_alpha") is None
    assert get_prompt_section("lifecycle.demo.banner") is None
    assert "lifecycle.demo.banner" not in list_prompt_sections()
    assert get_lifecycle_ledger().get(plugin_id) is None
    assert get_seam_registry().active_id("fs") != "fs.lifecycle_demo"
    events = list_audit_events(limit=5)
    assert any(e["action"] == "unmount" and e["plugin_id"] == plugin_id for e in events)


def test_double_enable_idempotent_double_disable_safe():
    mgr, ctx = _make_manager_and_ctx("lifecycle-idem")

    def _handler(args, **kwargs):
        return "{}"

    ctx.register_tool(
        name="lifecycle_test_beta",
        toolset="lifecycle_test",
        schema={"name": "lifecycle_test_beta", "description": "t", "parameters": {}},
        handler=_handler,
    )
    # Patch get_plugin_manager used by hot API
    import keprix.plugin_lifecycle.api as api
    import keprix_cli.plugins as plugins_mod

    monkey_mgr = mgr
    original = plugins_mod.get_plugin_manager
    plugins_mod.get_plugin_manager = lambda: monkey_mgr
    try:
        first = enable_plugin_hot("lifecycle-idem", who="test")
        second = enable_plugin_hot("lifecycle-idem", who="test")
        assert first["ok"] is True
        assert second.get("idempotent") is True
        d1 = disable_plugin_hot("lifecycle-idem", who="test")
        d2 = disable_plugin_hot("lifecycle-idem", who="test")
        assert d1["ok"] is True
        assert d2.get("idempotent") is True
        assert tool_registry.get_entry("lifecycle_test_beta") is None
    finally:
        plugins_mod.get_plugin_manager = original


def test_enable_disable_enable_restores_tools():
    mgr, ctx = _make_manager_and_ctx("lifecycle-cycle")

    def register(c: PluginContext) -> None:
        def _handler(args, **kwargs):
            return '{"restored": true}'

        c.register_tool(
            name="lifecycle_test_gamma",
            toolset="lifecycle_test",
            schema={"name": "lifecycle_test_gamma", "description": "t", "parameters": {}},
            handler=_handler,
        )
        c.register_prompt_section("lifecycle.cycle.section", "CYCLE")

    # Simulate plugin module register()
    import types

    mod = types.ModuleType("keprix_plugins_lifecycle_cycle")
    mod.register = register  # type: ignore[attr-defined]
    loaded = mgr._plugins["lifecycle-cycle"]
    loaded.module = mod
    register(ctx)

    assert tool_registry.get_entry("lifecycle_test_gamma") is not None
    mgr.unmount_plugin("lifecycle-cycle")
    assert tool_registry.get_entry("lifecycle_test_gamma") is None

    # Remount via _load_plugin path
    result = mgr.mount_plugin("lifecycle-cycle", who="test")
    assert result["ok"] is True
    assert tool_registry.get_entry("lifecycle_test_gamma") is not None
    assert get_prompt_section("lifecycle.cycle.section") == "CYCLE"


def test_soft_wall_still_blocks_after_reload(tmp_path):
    """Policy-wrapped shell seam still hardline-blocks after remount."""
    from keprix.seams.policy import PolicyWrappedShell
    from keprix.seams.providers import LocalShellProvider

    ensure_default_seams(force=True, sandbox_root=tmp_path / "sb")
    mgr, ctx = _make_manager_and_ctx("lifecycle-softwall")
    wrapped = PolicyWrappedShell(LocalShellProvider(tmp_path))
    ctx.register_seam_provider("shell", wrapped, make_active=True)

    shell = get_seam_registry().get("shell")
    blocked = shell.execute("rm -rf /")
    assert blocked.get("blocked") is True or blocked.get("returncode") == 126

    mgr.unmount_plugin("lifecycle-softwall")
    # Remount same provider contribution
    ctx2 = PluginContext(mgr._plugins["lifecycle-softwall"].manifest, mgr)
    ctx2.register_seam_provider(
        "shell",
        PolicyWrappedShell(LocalShellProvider(tmp_path)),
        make_active=True,
    )
    shell2 = get_seam_registry().get("shell")
    blocked2 = shell2.execute("rm -rf /")
    assert blocked2.get("error_code") == "hardline_blocked"


def test_no_cordis_or_dsh_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [str(d).lower() for d in pyproject.get("project", {}).get("dependencies", [])]
    for dep in deps:
        assert "cordis" not in dep
        assert "deepseek-harness" not in dep
