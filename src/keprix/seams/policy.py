"""Policy wrappers: Soft Wall, Channel Shield, and vault floors around Providers.

Wrappers sit *outside* Providers. Consumers still call the Definition API;
gates never become alternate consumers that skip the seam.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from keprix.seams.errors import SeamPolicyDenied
from keprix.seams.ids import SEAM_RELATED_TOOLS

GateFn = Callable[[str, dict[str, Any]], dict[str, Any] | None]
# Gate returns None to allow, or a dict with error_code/message to deny.


def default_shell_soft_wall_gate(action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Gate shell.execute via the unconditional hardline Soft Wall floor.

    Uses ``tools.approval.detect_hardline_command``. Interactive Soft Wall
    prompting for merely "dangerous" commands stays in the agent loop; this
    seam gate enforces the hardline floor so Providers cannot skip it.
    """
    del action
    command = str(payload.get("command") or "")
    if not command.strip():
        return None
    try:
        from tools.approval import detect_hardline_command
    except Exception:
        return None
    try:
        is_hardline, description = detect_hardline_command(command)
    except Exception:
        return None
    if is_hardline:
        return {
            "error_code": "hardline_blocked",
            "message": str(description or "hardline blocked"),
        }
    return None


def default_fs_vault_gate(action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Refuse FS writes into vault / credential floors."""
    path = str(payload.get("path") or "")
    if not path:
        return None
    lowered = path.replace("\\", "/").lower()
    vault_markers = (
        "/.keprix/vault",
        "/keprix-data/vault",
        "/.access/",
        "/credentials/",
        ".env",
        "id_rsa",
        "id_ed25519",
    )
    if action in {"write_text", "write"} and any(m in lowered for m in vault_markers):
        return {
            "error_code": "vault_floor_denied",
            "message": f"FS write denied by vault floor for path: {path}",
        }
    return None


def default_web_channel_shield_gate(
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Lightweight Channel Shield hint for untrusted inbound URL fetch.

    Full Channel Shield stays a first-class module; this gate only blocks
    clearly dangerous schemes before the web Provider runs.
    """
    del action
    url = str(payload.get("url") or "").strip().lower()
    if not url:
        return None
    if url.startswith(("file:", "javascript:", "data:")):
        return {
            "error_code": "channel_shield_scheme_denied",
            "message": f"Web fetch denied for scheme in URL: {url[:80]}",
        }
    return None


class PolicyWrappedFs:
    """Fs Provider wrapper that applies vault-floor Soft Wall gates."""

    def __init__(
        self,
        inner: Any,
        *,
        gate: GateFn | None = None,
        provider_id: str | None = None,
    ) -> None:
        self._inner = inner
        self._gate = gate or default_fs_vault_gate
        self.provider_id = provider_id or f"policy:{getattr(inner, 'provider_id', 'fs')}"

    def read_text(self, path: str, *, encoding: str = "utf-8") -> str:
        return self._inner.read_text(path, encoding=encoding)

    def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None:
        denial = self._gate("write_text", {"path": path, "content_len": len(content)})
        if denial:
            raise SeamPolicyDenied(
                str(denial.get("message") or "FS write denied"),
                error_code=str(denial.get("error_code") or "seam_policy_denied"),
            )
        return self._inner.write_text(path, content, encoding=encoding)

    def exists(self, path: str) -> bool:
        return self._inner.exists(path)

    def list_dir(self, path: str = ".") -> list[str]:
        return self._inner.list_dir(path)

    def tool_schemas(self) -> list[dict[str, Any]]:
        return self._inner.tool_schemas()


class PolicyWrappedShell:
    """Shell Provider wrapper that applies Soft Wall / hardline gates."""

    def __init__(
        self,
        inner: Any,
        *,
        gate: GateFn | None = None,
        provider_id: str | None = None,
    ) -> None:
        self._inner = inner
        self._gate = gate or default_shell_soft_wall_gate
        self.provider_id = provider_id or f"policy:{getattr(inner, 'provider_id', 'shell')}"

    def execute(
        self,
        command: str,
        *,
        cwd: str = "",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        denial = self._gate("execute", {"command": command, "cwd": cwd})
        if denial:
            return {
                "output": str(denial.get("message") or "blocked"),
                "returncode": 126,
                "error_code": denial.get("error_code") or "seam_policy_denied",
                "blocked": True,
            }
        return self._inner.execute(command, cwd=cwd, timeout=timeout)

    def tool_schemas(self) -> list[dict[str, Any]]:
        return self._inner.tool_schemas()


class PolicyWrappedWeb:
    """Web Provider wrapper that applies Channel Shield scheme gates."""

    def __init__(
        self,
        inner: Any,
        *,
        gate: GateFn | None = None,
        provider_id: str | None = None,
    ) -> None:
        self._inner = inner
        self._gate = gate or default_web_channel_shield_gate
        self.provider_id = provider_id or f"policy:{getattr(inner, 'provider_id', 'web')}"

    def search(self, query: str, *, limit: int = 5) -> dict[str, Any]:
        return self._inner.search(query, limit=limit)

    def fetch(self, url: str, **kwargs: Any) -> dict[str, Any]:
        denial = self._gate("fetch", {"url": url, **kwargs})
        if denial:
            raise SeamPolicyDenied(
                str(denial.get("message") or "Web fetch denied"),
                error_code=str(denial.get("error_code") or "seam_policy_denied"),
            )
        return self._inner.fetch(url, **kwargs)

    def tool_schemas(self) -> list[dict[str, Any]]:
        return self._inner.tool_schemas()


def related_tool_schema_stubs(seam: str) -> list[dict[str, Any]]:
    """Metadata schemas listing related tool names for a seam (not live tool registry)."""
    names = SEAM_RELATED_TOOLS.get(seam, ())  # type: ignore[arg-type]
    return [{"name": name, "seam": seam, "type": "related_tool"} for name in names]


def resolve_under_root(root: Path, path: str) -> Path:
    """Resolve *path* under *root*; raise SeamPolicyDenied on escape."""
    root_resolved = root.resolve()
    candidate = (root_resolved / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise SeamPolicyDenied(
            f"Path escapes sandbox root: {path}",
            error_code="sandbox_path_escape",
        ) from exc
    return candidate
