"""Async HTTP(S) credential injection proxy server."""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any
from urllib.parse import urlparse

import httpx

from keprix.proxy.certs import ensure_ca_material, ensure_host_certificate
from keprix.proxy.config import ProxyConfig, load_proxy_config
from keprix.proxy.injector import CredentialInjector
from keprix.proxy.ssrf import assert_host_allowed

logger = logging.getLogger(__name__)

DEFAULT_LISTEN = "127.0.0.1:6790"


def parse_listen(listen: str) -> tuple[str, int]:
    if ":" not in listen:
        return listen, 6790
    host, _, port = listen.rpartition(":")
    return host or "127.0.0.1", int(port)


def _headers_from_raw(raw_headers: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in raw_headers.split(b"\r\n"):
        if b":" not in line:
            continue
        name, value = line.split(b":", 1)
        headers[name.decode("latin-1").strip()] = value.decode("latin-1").strip()
    return headers


def _build_forward_headers(headers: dict[str, str]) -> dict[str, str]:
    skip = {"proxy-connection", "connection", "keep-alive", "transfer-encoding", "te", "trailers", "upgrade", "host"}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


async def _read_http_request(reader: asyncio.StreamReader) -> tuple[str, str, str, dict[str, str], bytes]:
    request_line = (await reader.readline()).decode("latin-1", errors="replace").strip()
    if not request_line:
        raise ValueError("empty request")
    method, target, version = request_line.split(" ", 2)
    header_lines: list[bytes] = []
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        header_lines.append(line.rstrip(b"\r\n"))
    headers = _headers_from_raw(b"\r\n".join(header_lines))
    body = b""
    if method.upper() in {"POST", "PUT", "PATCH"}:
        length = int(headers.get("Content-Length", "0") or "0")
        if length:
            body = await reader.readexactly(length)
    return method, target, version, headers, body


async def _forward_http(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    injector: CredentialInjector,
) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host:
        raise ValueError(f"Invalid URL {url!r}")
    merged = injector.inject_headers(host, _build_forward_headers(headers))
    async with httpx.AsyncClient(verify=True, timeout=120.0) as client:
        response = await client.request(method, url, headers=merged, content=body or None)
        return response.status_code, dict(response.headers), response.content


async def _write_http_response(writer: asyncio.StreamWriter, status: int, headers: dict[str, str], body: bytes) -> None:
    writer.write(_format_http_response(status, headers, body))
    await writer.drain()


def _format_http_response(status: int, headers: dict[str, str], body: bytes) -> bytes:
    reason = "OK" if status == 200 else "Error"
    lines = [f"HTTP/1.1 {status} {reason}\r\n"]
    headers = dict(headers)
    headers.setdefault("Content-Length", str(len(body)))
    headers.setdefault("Connection", "close")
    for key, value in headers.items():
        if key.lower() in {"transfer-encoding", "connection"}:
            continue
        lines.append(f"{key}: {value}\r\n")
    lines.append("\r\n")
    return "".join(lines).encode("latin-1") + body


async def _tunnel_bidirectional(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    remote_reader: asyncio.StreamReader,
    remote_writer: asyncio.StreamWriter,
) -> None:
    async def pump(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
        try:
            while True:
                chunk = await src.read(65536)
                if not chunk:
                    break
                dst.write(chunk)
                await dst.drain()
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                dst.close()
                await dst.wait_closed()
            except Exception:
                pass

    await asyncio.gather(
        pump(client_reader, remote_writer),
        pump(remote_reader, client_writer),
    )


async def _handle_connect_mitm(
    *,
    host: str,
    port: int,
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    injector: CredentialInjector,
) -> None:
    cert_path, key_path = ensure_host_certificate(host)
    client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await client_writer.drain()

    sock = client_writer.get_extra_info("socket")
    if sock is None:
        raise RuntimeError("Cannot access client socket for TLS MITM")

    sock.setblocking(False)
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    loop = asyncio.get_running_loop()
    ssl_sock = server_ctx.wrap_socket(sock, server_side=True, do_handshake_on_connect=False)

    while True:
        try:
            await loop.sock_recv(ssl_sock, 1)
            break
        except ssl.SSLWantReadError:
            await asyncio.sleep(0)
        except BlockingIOError:
            await asyncio.sleep(0)

    request_data = b""
    while b"\r\n\r\n" not in request_data:
        chunk = await loop.sock_recv(ssl_sock, 4096)
        if not chunk:
            break
        request_data += chunk

    header_blob, _, body_part = request_data.partition(b"\r\n\r\n")
    lines = header_blob.decode("latin-1", errors="replace").split("\r\n")
    method, target, _version = lines[0].split(" ", 2)
    headers = _headers_from_raw(header_blob)
    body = body_part
    content_length = int(headers.get("Content-Length", "0") or "0")
    while len(body) < content_length:
        body += await loop.sock_recv(ssl_sock, content_length - len(body))

    if target.startswith("http://") or target.startswith("https://"):
        url = target
    else:
        url = f"https://{host}:{port}{target}"
    status, resp_headers, resp_body = await _forward_http(
        method=method,
        url=url,
        headers=headers,
        body=body,
        injector=injector,
    )
    response = _format_http_response(status, resp_headers, resp_body)
    await loop.sock_sendall(ssl_sock, response)
    ssl_sock.close()


async def _handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    injector: CredentialInjector,
) -> None:
    try:
        method, target, _version, headers, body = await _read_http_request(client_reader)
        if method.upper() == "CONNECT":
            host, _, port_text = target.partition(":")
            port = int(port_text or "443")
            route = injector.route_for_host(host)
            if route is not None:
                await _handle_connect_mitm(
                    host=host,
                    port=port,
                    client_reader=client_reader,
                    client_writer=client_writer,
                    injector=injector,
                )
                return
            assert_host_allowed(host)
            remote_reader, remote_writer = await asyncio.open_connection(host, port)
            client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await client_writer.drain()
            await _tunnel_bidirectional(client_reader, client_writer, remote_reader, remote_writer)
            return

        if target.startswith("http://") or target.startswith("https://"):
            url = target
            host = urlparse(url).hostname or ""
        else:
            host = headers.get("Host", "").split(":")[0]
            url = f"http://{headers.get('Host', host)}{target}"

        if injector.route_for_host(host):
            status, resp_headers, resp_body = await _forward_http(
                method=method,
                url=url,
                headers=headers,
                body=body,
                injector=injector,
            )
            await _write_http_response(client_writer, status, resp_headers, resp_body)
            return

        parsed_host = urlparse(url).hostname or host
        assert_host_allowed(parsed_host)
        client_writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
    except PermissionError as exc:
        logger.warning("blocked request: %s", exc)
        client_writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
    except Exception as exc:
        logger.exception("proxy client error: %s", exc)
        client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await client_writer.drain()
    finally:
        client_writer.close()
        try:
            await client_writer.wait_closed()
        except Exception:
            pass


async def run_proxy_server(config: ProxyConfig | None = None) -> None:
    cfg = config or load_proxy_config()
    host, port = parse_listen(cfg.listen)
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Credential proxy must bind to localhost only")
    ensure_ca_material()
    injector = CredentialInjector(cfg)
    server = await asyncio.start_server(
        lambda r, w: _handle_client(r, w, injector),
        host=host,
        port=port,
    )
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    logger.info("credential proxy listening on %s", addrs)
    async with server:
        await server.serve_forever()


def run_proxy_server_sync(config: ProxyConfig | None = None) -> None:
    asyncio.run(run_proxy_server(config))
