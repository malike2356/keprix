"""Sidecar-only FastAPI process (port 3360 by default)."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI

from keprix.universal_sidecar.contract import DEFAULT_SIDECAR_HOST, DEFAULT_SIDECAR_PORT
from keprix.universal_sidecar.routes import router, set_shutting_down


def _is_loopback(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in {"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"}


def _has_secure_config() -> bool:
    if os.environ.get("KEPRIX_SIDECAR_TLS_CERT") or os.environ.get("KEPRIX_SIDECAR_TLS_KEY"):
        return True
    if os.environ.get("KEPRIX_UNIVERSAL_SIDECAR_TOKEN_SECRET", "").strip():
        return True
    if os.environ.get("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "").strip():
        return True
    if os.environ.get("KEPRIX_SIDECAR_AUTH_SECRET", "").strip():
        return True
    return False


def _refuse_insecure_public_bind(host: str) -> None:
    if _is_loopback(host):
        return
    if _has_secure_config():
        return
    if os.environ.get("KEPRIX_SIDECAR_ALLOW_PUBLIC", "").strip() == "1":
        print(
            "WARNING: Keprix sidecar binding to non-loopback host without TLS/auth secret. "
            "KEPRIX_SIDECAR_ALLOW_PUBLIC=1 is set. Do not use this in production.",
            file=sys.stderr,
        )
        return
    print(
        "Refusing to start: non-loopback bind requires TLS env or auth secret, "
        "or set KEPRIX_SIDECAR_ALLOW_PUBLIC=1 (development only).",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _load_config_on_startup() -> None:
    """Optional: KEPRIX_SIDECAR_CONFIG path to keprix.sidecar.yaml."""
    path = os.environ.get("KEPRIX_SIDECAR_CONFIG", "").strip()
    if not path:
        return
    from keprix.universal_sidecar.registry import get_project_registry

    get_project_registry().load_file(path, confirm_risky=True)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    set_shutting_down(False)
    try:
        _load_config_on_startup()
    except Exception as exc:  # pragma: no cover - startup diagnostics
        print(f"WARNING: failed to load KEPRIX_SIDECAR_CONFIG: {exc}", file=sys.stderr)
    yield
    set_shutting_down(True)


def create_sidecar_app() -> FastAPI:
    """Sidecar-only app: universal routes only (no admin/workspace UI)."""
    app = FastAPI(
        title="Keprix Universal Sidecar",
        version="1.0.0",
        lifespan=_lifespan,
    )
    app.include_router(router)
    return app


def main(argv: list[str] | None = None) -> None:
    del argv  # reserved for future CLI passthrough
    host = os.environ.get("KEPRIX_SIDECAR_HOST", DEFAULT_SIDECAR_HOST).strip() or DEFAULT_SIDECAR_HOST
    port_raw = os.environ.get("KEPRIX_SIDECAR_PORT", str(DEFAULT_SIDECAR_PORT)).strip()
    try:
        port = int(port_raw)
    except ValueError:
        print(f"Invalid KEPRIX_SIDECAR_PORT: {port_raw}", file=sys.stderr)
        raise SystemExit(2) from None
    _refuse_insecure_public_bind(host)
    import uvicorn

    uvicorn.run(
        "keprix.universal_sidecar.app:create_sidecar_app",
        factory=True,
        host=host,
        port=port,
        log_level=os.environ.get("KEPRIX_SIDECAR_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
