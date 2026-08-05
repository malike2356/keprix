from __future__ import annotations

from pathlib import Path


def _reset_config_caches(config_module) -> None:
    config_module._LOAD_CONFIG_CACHE.clear()
    config_module._RAW_CONFIG_CACHE.clear()
    config_module.invalidate_env_cache()


def test_legacy_hermes_config_is_read_when_keprix_config_missing(tmp_path, monkeypatch) -> None:
    from keprix_cli import config as config_module

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("KEPRIX_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    _reset_config_caches(config_module)

    legacy_home = tmp_path / ".hermes"
    legacy_home.mkdir()
    (legacy_home / "config.yaml").write_text("model:\n  default: legacy-model\n", encoding="utf-8")

    loaded = config_module.load_config()

    assert loaded["model"]["default"] == "legacy-model"


def test_save_config_writes_keprix_home_not_legacy_hermes_home(tmp_path, monkeypatch) -> None:
    from keprix_cli import config as config_module

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("KEPRIX_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    _reset_config_caches(config_module)

    legacy_home = tmp_path / ".hermes"
    legacy_home.mkdir()
    (legacy_home / "config.yaml").write_text("model:\n  default: legacy-model\n", encoding="utf-8")

    loaded = config_module.load_config()
    loaded["model"]["default"] = "keprix-model"
    config_module.save_config(loaded)

    assert (tmp_path / ".keprix" / "config.yaml").exists()
    assert "keprix-model" in (tmp_path / ".keprix" / "config.yaml").read_text(encoding="utf-8")
    assert "legacy-model" in (legacy_home / "config.yaml").read_text(encoding="utf-8")


def test_legacy_hermes_env_is_read_when_keprix_env_missing(tmp_path, monkeypatch) -> None:
    from keprix_cli import config as config_module

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("KEPRIX_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("KEPRIX_SAMPLE_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_SAMPLE_TOKEN", raising=False)
    _reset_config_caches(config_module)

    legacy_home = tmp_path / ".hermes"
    legacy_home.mkdir()
    (legacy_home / ".env").write_text("HERMES_SAMPLE_TOKEN=legacy\n", encoding="utf-8")

    assert config_module.get_env_value("KEPRIX_SAMPLE_TOKEN") == "legacy"


def test_keprix_env_wins_over_legacy_hermes_env(tmp_path, monkeypatch) -> None:
    from keprix_cli import config as config_module

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("KEPRIX_SAMPLE_TOKEN", "new")
    monkeypatch.setenv("HERMES_SAMPLE_TOKEN", "old")
    _reset_config_caches(config_module)

    assert config_module.get_env_value("KEPRIX_SAMPLE_TOKEN") == "new"


def test_keprix_env_file_wins_over_legacy_hermes_env_file(tmp_path, monkeypatch) -> None:
    from keprix_cli import config as config_module

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("KEPRIX_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("KEPRIX_SAMPLE_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_SAMPLE_TOKEN", raising=False)
    _reset_config_caches(config_module)

    keprix_home = tmp_path / ".keprix"
    legacy_home = tmp_path / ".hermes"
    keprix_home.mkdir()
    legacy_home.mkdir()
    (keprix_home / ".env").write_text("KEPRIX_SAMPLE_TOKEN=new\n", encoding="utf-8")
    (legacy_home / ".env").write_text("HERMES_SAMPLE_TOKEN=old\n", encoding="utf-8")

    assert config_module.get_env_value("KEPRIX_SAMPLE_TOKEN") == "new"
