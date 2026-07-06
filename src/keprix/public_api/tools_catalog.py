"""Tool catalog for the developer dashboard."""

from __future__ import annotations


def list_public_toolsets() -> list[str]:
    try:
        from gateway.run import _load_gateway_config
        from keprix_cli.tools_config import _get_platform_tools

        return sorted(_get_platform_tools(_load_gateway_config(), "api_server"))
    except Exception:
        return []
