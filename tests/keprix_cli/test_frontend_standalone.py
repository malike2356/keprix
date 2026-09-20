"""Unit tests for keprix_cli.frontend_standalone helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix_cli import frontend_standalone as fe


def test_normalize_module_name_scoped_and_plain():
    assert fe._normalize_module_name("styled-jsx/package.json") == "styled-jsx"
    assert fe._normalize_module_name("@swc/helpers/_/_interop_require_default") == "@swc/helpers"
    assert fe._normalize_module_name("@next/env") == "@next/env"
    assert fe._normalize_module_name("client-only") == "client-only"


def test_frontend_build_needed_missing_sentinel(tmp_path, monkeypatch):
    monkeypatch.setattr(fe, "FRONTEND_DIST", tmp_path / "frontend_dist")
    monkeypatch.setattr(fe, "_BUILD_META_FILE", tmp_path / "frontend_dist" / ".keprix-build-meta.json")
    monkeypatch.setattr(fe, "FRONTEND_SRC", tmp_path / "frontend")
    assert fe._frontend_build_needed("http://127.0.0.1:9119") is True


def test_frontend_build_needed_backend_url_mismatch(tmp_path, monkeypatch):
    dist = tmp_path / "frontend_dist"
    dist.mkdir()
    (dist / "server.js").write_text("// sentinel\n")
    meta = dist / ".keprix-build-meta.json"
    meta.write_text(json.dumps({"backend_url": "http://127.0.0.1:9119"}))
    src = tmp_path / "frontend"
    (src / "src").mkdir(parents=True)

    monkeypatch.setattr(fe, "FRONTEND_DIST", dist)
    monkeypatch.setattr(fe, "_BUILD_META_FILE", meta)
    monkeypatch.setattr(fe, "FRONTEND_SRC", src)

    assert fe._frontend_build_needed("http://127.0.0.1:9119") is False
    assert fe._frontend_build_needed("http://127.0.0.1:9130") is True


def test_write_build_meta(tmp_path, monkeypatch):
    dist = tmp_path / "frontend_dist"
    monkeypatch.setattr(fe, "FRONTEND_DIST", dist)
    monkeypatch.setattr(fe, "_BUILD_META_FILE", dist / ".keprix-build-meta.json")
    fe._write_build_meta("http://127.0.0.1:9119")
    data = json.loads((dist / ".keprix-build-meta.json").read_text())
    assert data["backend_url"] == "http://127.0.0.1:9119"
    assert "built_at" in data


def test_copy_next_middleware_into_dist(tmp_path):
    next_dir = tmp_path / ".next"
    src_mw = next_dir / "server" / "src"
    src_mw.mkdir(parents=True)
    (src_mw / "middleware.js").write_text("export function middleware() {}")
    (next_dir / "server" / "edge-runtime-webpack.js").write_text("// edge\n")
    dest = tmp_path / "frontend_dist"
    dest.mkdir()
    fe._copy_next_middleware_into_dist(next_dir, dest)
    assert (dest / ".next" / "server" / "src" / "middleware.js").is_file()
    assert (dest / ".next" / "server" / "edge-runtime-webpack.js").is_file()
    blob = "Error: Cannot find module 'client-only'\nRequire stack:\n- /tmp/x.js\n"
    assert fe._extract_missing_module(blob) == "client-only"
    blob2 = "Error: Cannot find module '@swc/helpers/_/_interop_require_default'\n"
    assert fe._extract_missing_module(blob2) == "@swc/helpers"
    assert fe._extract_missing_module("all good") is None
