"""Stable Keprix wrapper for Graphiti MCP HTTP (streamable) or built-in local store."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse, urlunparse

from keprix.brain.graphiti_local import LocalGraphitiStore

_BUILTIN_URLS = {"", "builtin", "local", "local://", "builtin://graphiti"}


def graphiti_enabled() -> bool:
    return os.getenv("KEPRIX_GRAPHITI_ENABLED", "1").lower() not in {"0", "false", "no"}


def graphiti_url() -> str:
    return os.getenv("GRAPHITI_MCP_URL", "").strip()


def uses_builtin_graphiti(url: str | None = None) -> bool:
    value = (graphiti_url() if url is None else url).strip().lower()
    return value in _BUILTIN_URLS


def masked_url() -> str:
    if uses_builtin_graphiti():
        return "builtin://graphiti"
    url = graphiti_url()
    if not url:
        return ""
    if "@" in url:
        prefix, suffix = url.rsplit("@", 1)
        return f"{prefix.split('://', 1)[0]}://***@{suffix}" if "://" in prefix else f"***@{suffix}"
    return url


def _health_url(mcp_url: str) -> str:
    parsed = urlparse(mcp_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/mcp"):
        path = path[: -len("/mcp")] or "/"
    elif path.endswith("/mcp/"):
        path = path[: -len("/mcp/")] or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/") + "/health", "", "", ""))


def _mcp_endpoint(mcp_url: str) -> str:
    return mcp_url.rstrip("/")


def _parse_sse_json(raw: str) -> Any:
    data_lines = [line[6:] for line in raw.splitlines() if line.startswith("data: ")]
    if not data_lines:
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {"raw": raw}
    return json.loads(data_lines[-1])


def _unwrap_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload if isinstance(payload, dict) else {"raw": payload}
    if isinstance(result.get("structuredContent"), dict):
        structured = result["structuredContent"]
        if isinstance(structured.get("result"), dict):
            return structured["result"]
        return structured
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and isinstance(first.get("text"), str):
            try:
                parsed = json.loads(first["text"])
                return parsed if isinstance(parsed, dict) else {"raw": parsed}
            except json.JSONDecodeError:
                return {"message": first["text"]}
    return result


class GraphitiMcpClient:
    """Minimal streamable-HTTP MCP client for Graphiti."""

    def __init__(self, base_url: str, timeout: int = 60) -> None:
        self.base_url = _mcp_endpoint(base_url)
        self.timeout = timeout
        self.session_id: str | None = None
        self._req_id = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def ensure_session(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "keprix-graphiti-bridge", "version": "1"},
            },
        )
        self._rpc("notifications/initialized", {}, notification=True)
        self._initialized = True

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self.ensure_session()
        payload = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        return _unwrap_tool_result(payload if isinstance(payload, dict) else {"raw": payload})

    def _rpc(self, method: str, params: dict[str, Any] | None = None, *, notification: bool = False) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notification:
            body["id"] = self._next_id()
        if params is not None:
            body["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            # Graphiti MCP's HTTP app rejects non-localhost Host values by default.
            "Host": "localhost:8000",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if not self.session_id:
                    headers_map = getattr(response, "headers", None)
                    if headers_map is not None:
                        self.session_id = headers_map.get("mcp-session-id")
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Graphiti MCP returned HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError(f"Graphiti MCP unreachable: {exc}") from exc
        if notification:
            return {}
        return _parse_sse_json(raw)


class GraphitiBridge:
    def __init__(self, base_url: str | None = None, timeout: int = 60) -> None:
        self.timeout = timeout
        if base_url is None:
            configured = graphiti_url()
            use_local = uses_builtin_graphiti(configured)
            self.base_url = "" if use_local else configured.rstrip("/")
            self._local = LocalGraphitiStore() if use_local else None
            self._mcp = None if use_local else GraphitiMcpClient(self.base_url, timeout=timeout)
            return
        cleaned = base_url.strip().rstrip("/")
        if uses_builtin_graphiti(cleaned):
            self.base_url = ""
            self._local = LocalGraphitiStore()
            self._mcp = None
        else:
            self.base_url = cleaned
            self._local = None
            self._mcp = GraphitiMcpClient(self.base_url, timeout=timeout)

    def status(self) -> dict[str, Any]:
        if not graphiti_enabled():
            return {"status": "disabled", "url": masked_url()}
        if self._local is not None:
            health = self._local.handle("health", {})
            return {
                "status": "connected",
                "url": "builtin://graphiti",
                "backend": "builtin",
                "episodes": health.get("episodes", 0),
            }
        if not self.base_url:
            return {"status": "misconfigured", "url": ""}
        try:
            health = self._http_json(_health_url(self.base_url))
            ok = isinstance(health, dict) and str(health.get("status", "")).lower() in {"healthy", "ok"}
            if not ok and self._mcp is not None:
                tool = self._mcp.call_tool("get_status", {})
                ok = str(tool.get("status", "")).lower() in {"ok", "healthy"}
            if ok:
                return {"status": "connected", "url": masked_url(), "backend": "mcp", "health": health}
            return {"status": "unreachable", "url": masked_url(), "error": str(health), "backend": "mcp"}
        except Exception as exc:
            return {"status": "unreachable", "url": masked_url(), "error": str(exc), "backend": "mcp"}

    def add_episode(self, *, name: str, content: str, source_ref: str) -> dict[str, Any]:
        if self._local is not None:
            return self._local.handle(
                "add_episode",
                {"name": name, "episode_body": content, "source": source_ref},
            )
        assert self._mcp is not None
        queued = self._mcp.call_tool(
            "add_memory",
            {
                "name": name,
                "episode_body": content,
                "source": "text",
                "source_description": source_ref,
            },
        )
        return {
            "episode_id": str(queued.get("episode_id") or queued.get("uuid") or name),
            "id": str(queued.get("episode_id") or queued.get("uuid") or name),
            "nodes_added": int(queued.get("nodes_added") or 0),
            "edges_added": int(queued.get("edges_added") or 0),
            "message": queued.get("message"),
            "raw": queued,
        }

    def query(self, query: str, *, max_results: int = 10, include_sources: bool = True) -> dict[str, Any]:
        if self._local is not None:
            return self._local.handle(
                "search",
                {"query": query, "max_results": max_results, "include_sources": include_sources},
            )
        assert self._mcp is not None
        facts = self._mcp.call_tool(
            "search_memory_facts",
            {"query": query, "max_facts": max_results},
        )
        nodes = self._mcp.call_tool(
            "search_nodes",
            {"query": query, "max_nodes": max_results},
        )
        hits: list[dict[str, Any]] = []
        for item in facts.get("facts") or facts.get("edges") or []:
            if isinstance(item, dict):
                hits.append(
                    {
                        "fact": item.get("fact") or item.get("content") or str(item),
                        "source": item.get("source_node") if include_sources else None,
                        "raw": item,
                    }
                )
            else:
                hits.append({"fact": str(item)})
        for item in nodes.get("nodes") or []:
            if isinstance(item, dict):
                hits.append(
                    {
                        "fact": item.get("name") or item.get("summary") or str(item),
                        "source": "node" if include_sources else None,
                        "raw": item,
                    }
                )
        return {"hits": hits[:max_results], "results": hits[:max_results], "facts": facts, "nodes": nodes}

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        if self._local is not None:
            return self._local.handle("get_entity", {"entity_id": entity_id})
        assert self._mcp is not None
        try:
            return self._mcp.call_tool("get_entity_edge", {"uuid": entity_id})
        except RuntimeError:
            return self._mcp.call_tool("search_nodes", {"query": entity_id, "max_nodes": 1})

    def _call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        # retained for older tests that patch urllib around generic HTTP posts
        if self._local is not None:
            return self._local.handle(tool, arguments)
        if tool == "health":
            return self.status()
        if tool == "add_episode":
            return self.add_episode(
                name=str(arguments.get("name") or "episode"),
                content=str(arguments.get("episode_body") or arguments.get("content") or ""),
                source_ref=str(arguments.get("source") or arguments.get("source_ref") or ""),
            )
        if tool in {"search", "query"}:
            return self.query(
                str(arguments.get("query") or ""),
                max_results=int(arguments.get("max_results") or 10),
                include_sources=bool(arguments.get("include_sources", True)),
            )
        if tool == "get_entity":
            return self.get_entity(str(arguments.get("entity_id") or ""))
        assert self._mcp is not None
        return self._mcp.call_tool(tool, arguments)

    @staticmethod
    def _simple_triplets(content: str) -> list[tuple[str, str, str]]:
        text = " ".join((content or "").split())
        if not text:
            return []
        patterns = [
            re.compile(r"(?P<source>[A-Z][\w-]{1,40})\s+(?P<fact>partnered with|worked with|acquired|hired|joined|moved to|built|launched)\s+(?P<target>[A-Z][\w-]{1,40})", re.I),
            re.compile(r"(?P<source>[A-Z][\w-]{1,40})\s+(?P<fact>is|was)\s+(?P<target>[A-Za-z][\w\s-]{1,40})", re.I),
        ]
        found: list[tuple[str, str, str]] = []
        for pattern in patterns:
            for match in pattern.finditer(text):
                source = match.group("source").strip()
                fact = match.group("fact").strip().lower()
                target = match.group("target").strip()
                if source and target and source.lower() != target.lower():
                    found.append((source, fact, target))
        if found:
            return found
        tokens = [tok for tok in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)][:8]
        pairs = []
        for left, right in zip(tokens, tokens[1:]):
            pairs.append((left, "related_to", right))
        return pairs

    def _http_json(self, url: str) -> Any:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
