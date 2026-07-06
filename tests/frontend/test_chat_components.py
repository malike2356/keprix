"""Chat WebUI component guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAT = ROOT / "frontend" / "src" / "components" / "chat"


def test_chat_webui_components_exist() -> None:
    required = [
        "ModelSelector.tsx",
        "SessionList.tsx",
        "ChatShellNav.tsx",
        "ThinkingBlock.tsx",
        "ChatEmptyState.tsx",
        "ChatErrorBanner.tsx",
        "TypingIndicator.tsx",
    ]
    for name in required:
        assert (CHAT / name).is_file(), name


def test_chat_hooks_exist() -> None:
    hooks = ROOT / "frontend" / "src" / "hooks"
    assert (hooks / "useModelSelector.ts").is_file()
    assert (hooks / "useSessionList.ts").is_file()
    assert (hooks / "useStartNewConversation.ts").is_file()


def test_new_chat_page_does_not_auto_redirect_to_existing_session() -> None:
    page = ROOT / "frontend" / "src" / "app" / "(workspace)" / "chat" / "page.tsx"
    text = page.read_text(encoding="utf-8")
    assert "sessions[0]" not in text
    assert "useStartNewConversation" in text


def test_keprix_logo_uses_theme_text_in_workspace_mode() -> None:
    logo = (ROOT / "frontend" / "src" / "components" / "shared" / "KeprixLogo.tsx").read_text(
        encoding="utf-8"
    )
    assert 'color: onDark ? KEPRIX_COLORS.textPrimary : "text.primary"' in logo


def test_chat_shell_has_launcher_and_dashboard_links() -> None:
    header = (ROOT / "frontend" / "src" / "components" / "workspace" / "WorkspaceHeader.tsx").read_text(
        encoding="utf-8"
    )
    session_list = (CHAT / "SessionList.tsx").read_text(encoding="utf-8")
    nav = (CHAT / "ChatShellNav.tsx").read_text(encoding="utf-8")
    assert "ChatShellNav" in header
    assert "/launcher" in nav
    assert "/dashboard" in nav
    assert "ChatShellNav" in session_list
    assert "/launcher" in session_list


def test_new_conversation_buttons_create_sessions_directly() -> None:
    session_list = (CHAT / "SessionList.tsx").read_text(encoding="utf-8")
    sidebar = (ROOT / "frontend" / "src" / "components" / "workspace" / "WorkspaceSidebar.tsx").read_text(
        encoding="utf-8"
    )
    assert "startNewConversation" in session_list
    assert 'href="/chat"' not in session_list
    assert "startNewConversation" in sidebar
    assert 'href="/chat"' not in sidebar.split("New conversation")[0]
