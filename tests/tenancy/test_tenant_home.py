from __future__ import annotations

from pathlib import Path

import pytest

from keprix_constants import get_keprix_home
from keprix.security.product_context import ProductContext, clear_product_context, set_product_context
from keprix.tenancy.home import shared_soul_write_error, soul_path, tenant_home, tenant_home_scope


def test_tenant_home_is_below_data_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / "root"))
    assert tenant_home("tenant-a") == (tmp_path / "root" / "tenants" / "tenant-a").resolve()


def test_tenant_home_rejects_path_traversal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / "root"))
    with pytest.raises(ValueError):
        tenant_home("../other")


def test_tenant_home_scope_resets_after_exception(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / "root"))
    original = get_keprix_home()
    with pytest.raises(RuntimeError):
        with tenant_home_scope("tenant-a") as home:
            assert get_keprix_home() == home
            raise RuntimeError("test")
    assert get_keprix_home() == original


def test_product_context_selects_tenant_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / "root"))
    monkeypatch.setenv("KEPRIX_TENANT_HOME_ISOLATION", "1")
    token = set_product_context(ProductContext(product_id="keprix", workspace_id="a", tenant_id="tenant-a"))
    try:
        assert get_keprix_home() == (tmp_path / "root" / "tenants" / "tenant-a").resolve()
    finally:
        clear_product_context(token)


def test_tenant_soul_overrides_shared_without_bleeding(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_TENANT_HOME_ISOLATION", "1")
    root.mkdir()
    (root / "SOUL.md").write_text("shared", encoding="utf-8")
    tenant_a = tenant_home("tenant-a")
    tenant_b = tenant_home("tenant-b")
    tenant_a.mkdir(parents=True)
    tenant_b.mkdir(parents=True)
    (tenant_a / "SOUL.md").write_text("a", encoding="utf-8")
    (tenant_b / "SOUL.md").write_text("b", encoding="utf-8")
    for tenant, expected in (("tenant-a", "a"), ("tenant-b", "b")):
        token = set_product_context(ProductContext(product_id="keprix", workspace_id=tenant, tenant_id=tenant))
        try:
            assert soul_path().read_text(encoding="utf-8") == expected
            assert shared_soul_write_error(root / "SOUL.md")
            assert shared_soul_write_error(tenant_home(tenant) / "SOUL.md") is None
        finally:
            clear_product_context(token)


def test_tenant_without_soul_reads_shared_base(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_TENANT_HOME_ISOLATION", "1")
    root.mkdir()
    shared = root / "SOUL.md"
    shared.write_text("shared", encoding="utf-8")
    token = set_product_context(ProductContext(product_id="keprix", workspace_id="tenant-a", tenant_id="tenant-a"))
    try:
        assert soul_path() == shared
    finally:
        clear_product_context(token)
