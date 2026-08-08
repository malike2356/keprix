"""Frontend guards for Tool ACL admin console (prompt 468)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tool_acl_page_exists_and_wires_api() -> None:
    page = (ROOT / "frontend/src/app/(workspace)/admin/tool-acl/page.tsx").read_text(
        encoding="utf-8"
    )
    assert "Tool ACL" in page
    assert "tool-acl-api" in page or "@/lib/tool-acl-api" in page
    assert "listAclProducts" in page or "listResourceGrants" in page
    assert "Check playground" in page or "Check playground" in page.replace("\n", " ")
    assert "Admin role required" in page
    assert "/admin/tools" in page  # link to generated tools, not as self


def test_tool_acl_api_client_covers_endpoints() -> None:
    api = (ROOT / "frontend/src/lib/tool-acl-api.ts").read_text(encoding="utf-8")
    for path in (
        "/api/security/acl/products",
        "/api/security/acl/check",
        "/api/security/acl/audit",
        "/api/security/acl/resources/catalog",
        "/api/security/acl/resources/grants",
        "/api/security/acl/resources/check",
        "/api/security/acl/resources/broad",
    ):
        assert path in api, f"missing client path {path}"


def test_admin_tool_acl_nav_href_is_not_mutation_tools() -> None:
    py = (ROOT / "src/keprix/ui_contract/navigation.py").read_text(encoding="utf-8")
    ts = (ROOT / "frontend/src/lib/navigation.ts").read_text(encoding="utf-8")
    assert '"admin-tool-acl"' in py or "'admin-tool-acl'" in py
    assert 'id: "admin-tool-acl"' in ts
    # Exact anti-pattern: Tool ACL labeled but pointing at /admin/tools
    assert (
        '{"id": "admin-tool-acl", "label": "Tool ACL", "href": "/admin/tools"' not in py
    )
    assert (
        '{ id: "admin-tool-acl", label: "Tool ACL", href: "/admin/tools"' not in ts
    )
    assert '"href": "/admin/tool-acl"' in py or "href\": \"/admin/tool-acl\"" in py
    assert 'href: "/admin/tool-acl"' in ts


def test_tool_acl_docs_exist() -> None:
    doc = (ROOT / "docs/features/tool-acl.md").read_text(encoding="utf-8")
    assert "/admin/tool-acl" in doc
    assert "/admin/tools" in doc
    resource = (ROOT / "docs/features/resource-tool-acl.md").read_text(encoding="utf-8")
    assert "/admin/tool-acl" in resource
    assert "resource grant editor" not in resource.lower() or "/admin/tool-acl" in resource
