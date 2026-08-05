from keprix.tui.theme_system import available_themes, theme_contrast_report, theme_passes_contrast


def test_all_theme_tokens_meet_contrast_floor() -> None:
    for theme_name in available_themes():
        report = theme_contrast_report(theme_name)
        assert theme_passes_contrast(theme_name), (theme_name, report)
        assert min(report.values()) >= 4.5


def test_contrast_report_covers_required_surfaces() -> None:
    report = theme_contrast_report("Keprix Matrix")

    assert set(report) == {
        "accent",
        "cockpit",
        "error",
        "muted",
        "overlay",
        "selected",
        "text",
        "timeline",
        "tool",
        "warning",
    }
