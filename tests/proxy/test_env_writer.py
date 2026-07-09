"""Tests for proxy environment variable writer."""

from __future__ import annotations

from keprix.proxy.config import ProxyConfig
from keprix.proxy.env_writer import print_proxy_env, proxy_env_vars, write_proxy_env


def test_proxy_env_vars_include_dummy_keys_and_proxy_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    config = ProxyConfig(listen="127.0.0.1:6790")
    env = proxy_env_vars(config)
    assert env["HTTP_PROXY"] == "http://127.0.0.1:6790"
    assert env["HTTPS_PROXY"] == "http://127.0.0.1:6790"
    assert env["ANTHROPIC_API_KEY"] == "dummy-replaced-by-proxy"
    assert env["SSL_CERT_FILE"].endswith("ca.crt")
    assert (tmp_path / "proxy-ca").is_dir()


def test_write_proxy_env_merges_existing_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    env_path = tmp_path / ".env"
    env_path.write_text("CUSTOM_FLAG=1\nANTHROPIC_API_KEY=real-key\n", encoding="utf-8")
    write_proxy_env(ProxyConfig(), env_path=env_path)
    text = env_path.read_text(encoding="utf-8")
    assert "CUSTOM_FLAG=1" in text
    assert "ANTHROPIC_API_KEY=dummy-replaced-by-proxy" in text
    assert (tmp_path / ".proxy-env").is_file()


def test_print_proxy_env_exports(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    output = print_proxy_env(ProxyConfig())
    assert 'export HTTP_PROXY="http://127.0.0.1:6790"' in output
    assert "dummy-replaced-by-proxy" in output
