import pytest

from keprix.tui.client import KeprixClient
from keprix.tui.command_center.palette import dispatch_for_action
from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.theme_system import available_themes, normalize_theme_name, theme_class_names, theme_tokens
from keprix.tui.app import KeprixTuiApp


class OfflineClient(KeprixClient):
    async def health_check(self) -> bool:
        return False


def test_exactly_three_themes_are_available() -> None:
    assert available_themes() == ("Keprix Matrix", "Focus Light", "Operator Dark")
    assert len(theme_class_names()) == 3


def test_theme_name_normalization_accepts_cli_forms() -> None:
    assert normalize_theme_name("focus-light") == "Focus Light"
    assert normalize_theme_name("operator_dark") == "Operator Dark"
    assert normalize_theme_name("unknown") == "Keprix Matrix"


def test_command_center_exposes_theme_actions() -> None:
    registry = build_default_registry()
    actions = [action for action in registry.all() if action.category == "Themes"]

    assert [action.title for action in actions] == ["Focus Light", "Keprix Matrix", "Operator Dark"]
    result = dispatch_for_action(next(action for action in actions if action.title == "Operator Dark"))
    assert result.dispatch_kind == "switch_theme"
    assert result.value == "Operator Dark"


def test_app_set_theme_updates_current_theme(monkeypatch) -> None:
    saved: list[str] = []

    def fake_save(value: str) -> str:
        saved.append(value)
        return normalize_theme_name(value)

    monkeypatch.setattr("keprix.tui.app.save_theme_preference", fake_save)
    app = KeprixTuiApp(client=KeprixClient())

    assert app._set_theme("focus light") == "Focus Light"
    assert app._theme_name == "Focus Light"
    assert saved == ["focus light"]
    assert theme_tokens(app._theme_name).class_name == "theme-focus-light"


@pytest.mark.asyncio
async def test_app_stylesheet_compiles_in_textual_runtime() -> None:
    app = KeprixTuiApp(client=OfflineClient())

    async with app.run_test(size=(100, 32)):
        assert app.is_mounted
