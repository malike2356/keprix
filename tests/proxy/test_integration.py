"""End-to-end credential proxy HTTP forwarding tests."""

from __future__ import annotations

import asyncio
import json
import socket
from unittest.mock import AsyncMock, patch

import pytest

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.paths import local_vault_path
from keprix.proxy.server import run_proxy_server


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.mark.asyncio
async def test_proxy_forwards_matched_route_with_injected_header(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(
        json.dumps({"secrets": {"anthropic-api-key": "injected-secret"}}),
        encoding="utf-8",
    )
    port = _free_port()
    config = ProxyConfig(
        listen=f"127.0.0.1:{port}",
        routes=[
            RouteConfig(
                host="api.anthropic.com",
                header_name="x-api-key",
                secret_ref="anthropic-api-key",
            )
        ],
    )

    captured: dict[str, str] = {}

    async def fake_request(self, method, url, headers=None, content=None):
        captured["method"] = method
        captured["url"] = url
        captured["header"] = (headers or {}).get("x-api-key", "")
        response = AsyncMock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"ok": true}'
        return response

    server_task = asyncio.create_task(run_proxy_server(config))
    await asyncio.sleep(0.2)

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        request = (
            "GET https://api.anthropic.com/v1/models HTTP/1.1\r\n"
            "Host: api.anthropic.com\r\n"
            "Connection: close\r\n\r\n"
        )
        with patch("keprix.proxy.server.httpx.AsyncClient.request", new=fake_request):
            writer.write(request.encode("latin-1"))
            await writer.drain()
            response = await reader.read(4096)
        assert b"200" in response
        assert captured["header"] == "injected-secret"
        assert "api.anthropic.com" in captured["url"]
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        writer.close()
        await writer.wait_closed()
