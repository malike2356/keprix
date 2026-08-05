"""Guards for built apps navigation prompts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sidebar_collapse_files_exist() -> None:
    assert (ROOT / "frontend/src/components/shell/SidebarNavGroup.tsx").is_file()
    assert (ROOT / "frontend/src/hooks/useSidebarGroupState.ts").is_file()


def test_sidebar_uses_group_state_hook() -> None:
    sidebar = (ROOT / "frontend/src/components/shell/Sidebar.tsx").read_text(encoding="utf-8")
    assert "useSidebarGroupState" in sidebar
    assert "SidebarNavGroup" in sidebar


def test_built_app_layout_primitives_exist() -> None:
    built_app_dir = ROOT / "frontend/src/components/built-app"
    assert (built_app_dir / "types.ts").is_file()
    assert (built_app_dir / "BuiltAppLayout.tsx").is_file()
    assert (built_app_dir / "BuiltAppHeader.tsx").is_file()
    assert (built_app_dir / "BuiltAppSectionNav.tsx").is_file()
    assert (built_app_dir / "BuiltAppSubRail.tsx").is_file()
    assert (built_app_dir / "index.ts").is_file()
    assert (ROOT / "frontend/src/lib/built-app-manifest.ts").is_file()


def test_built_apps_registry_and_api_files_exist() -> None:
    assert (ROOT / "src/keprix/built_apps/manifest.py").is_file()
    assert (ROOT / "src/keprix/built_apps/registry.py").is_file()
    assert (ROOT / "src/keprix/built_apps/routes.py").is_file()
    assert (ROOT / "frontend/src/lib/built-apps-api.ts").is_file()
    assert (ROOT / "examples/built-app-starter/built_app.yaml").is_file()


def test_built_app_route_host_files_exist() -> None:
    route_dir = ROOT / "frontend/src/app/(workspace)/apps/[slug]"
    assert (route_dir / "layout.tsx").is_file()
    assert (route_dir / "page.tsx").is_file()
    assert (route_dir / "[section]/page.tsx").is_file()
    assert (ROOT / "frontend/src/hooks/useBuiltAppManifest.ts").is_file()


def test_built_app_route_layout_imports_shell_primitives() -> None:
    layout = (ROOT / "frontend/src/app/(workspace)/apps/[slug]/layout.tsx").read_text(encoding="utf-8")
    assert "BuiltAppLayout" in layout
    assert "useBuiltAppManifest" in layout
