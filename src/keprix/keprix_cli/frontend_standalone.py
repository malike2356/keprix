"""Build and run the standalone Next.js dashboard frontend as a managed child process.

``keprix dashboard`` is a single-process CLI experience, but the dashboard
frontend (``frontend/``) is a Next.js app built with ``output: "standalone"``
(a runnable Node *server*, not static HTML); the same artifact the Docker
Compose deployment runs as its own ``keprix-frontend`` container
(``docker/Dockerfile.frontend``). A standalone Next.js build cannot be
mounted as static files by FastAPI; it needs its own Node process.

This module owns that: building the standalone bundle (mirroring
``docker/Dockerfile.frontend``'s runner-stage COPY steps exactly, via
``shutil`` instead of Docker COPY), and spawning/health-checking it as a
sibling process to the Python backend, the same two-process shape Docker
already uses. ``frontend/next.config.ts`` already rewrites ``/api/*`` (and a
few other paths) to ``BACKEND_REWRITE_URL`` server-side, so no Python-side
HTTP/WebSocket reverse proxy is needed here; the frontend does its own
backend proxying exactly as it does in Docker.

Only works for an editable/source-checkout install (``pip install -e .`` /
``scripts/install.sh``, which is how the dashboard's frontend auto-build has
always effectively required things to be set up; the legacy ``web/``-based
Vite build had the identical constraint). A plain non-editable
``pipx install '.[tui]' --force`` has no ``frontend/`` sibling to build from
at runtime; ``build_frontend_standalone()`` detects that case and says so
plainly rather than failing silently.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# main.py's PROJECT_ROOT is src/keprix/ (the package source root); frontend/
# is a repo-root sibling of src/, i.e. two levels further up. Only correct
# for an editable/source-checkout install; see module docstring.
_PACKAGE_ROOT = Path(__file__).parent.parent.resolve()
REPO_ROOT = _PACKAGE_ROOT.parent.parent
FRONTEND_SRC = REPO_ROOT / "frontend"
FRONTEND_DIST = _PACKAGE_ROOT / "keprix_cli" / "frontend_dist"

_SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".css", ".mjs", ".cjs")
_SKIP_DIRS = frozenset({"node_modules", ".next", ".turbo"})
_BUILD_META_FILE = FRONTEND_DIST / ".keprix-build-meta.json"

# Packages the Next.js standalone tracer (@vercel/nft) has repeatedly missed
# under this repo's pnpm lockfile. Seeded before the iterative heal loop so
# cold boot and the first page request don't each pay a failed probe.
_KNOWN_TRACE_GAPS = (
    "styled-jsx",
    "@swc/helpers",
    "@next/env",
    "client-only",
)

_MODULE_NOT_FOUND = re.compile(r"Cannot find module '([^']+)'")


def _say(text: str) -> None:
    """Console-encoding-safe print (mirrors main.py's _build_web_ui helper)."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def frontend_source_available() -> bool:
    """True if this looks like an editable/source-checkout install with frontend/ present."""
    return (FRONTEND_SRC / "package.json").exists()


def _backend_url_mismatch(backend_url: str) -> bool:
    """True when the assembled dist was baked for a different rewrite target."""
    try:
        recorded = json.loads(_BUILD_META_FILE.read_text())
    except Exception:
        return True
    return recorded.get("backend_url") != backend_url


def _frontend_build_needed(backend_url: str) -> bool:
    """Return True if the standalone dist is missing, stale, or built for a different backend.

    Mirrors main.py's ``_web_ui_build_needed()`` for the mtime check, plus one
    thing that check doesn't need to care about: ``frontend/next.config.ts``'s
    ``rewrites()`` (the ``/api/*`` -> ``BACKEND_REWRITE_URL`` proxy) is
    resolved by Next.js when ``next build`` runs, not read fresh at server
    start. Confirmed via docker/Dockerfile.frontend, which sets it as a
    build ARG before ``pnpm exec next build`` for exactly this reason. So a
    build for backend port A cannot serve backend port B's rewrites; if the
    requested backend_url differs from what's recorded in the last build's
    meta file, that alone forces a rebuild even with unchanged source.
    """
    sentinel = FRONTEND_DIST / "server.js"
    if not sentinel.exists():
        return True
    if _backend_url_mismatch(backend_url):
        return True
    dist_mtime = sentinel.stat().st_mtime
    for base in (FRONTEND_SRC / "src", FRONTEND_SRC / "public"):
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base, topdown=True):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(_SOURCE_EXTENSIONS):
                    full = os.path.join(dirpath, fn)
                    if os.path.getmtime(full) > dist_mtime:
                        return True
    return False


def frontend_dist_matches_backend(backend_url: str) -> bool:
    """True when FRONTEND_DIST exists and was assembled for this backend_url."""
    return (FRONTEND_DIST / "server.js").exists() and not _frontend_build_needed(backend_url)


def _write_build_meta(backend_url: str) -> None:
    FRONTEND_DIST.mkdir(parents=True, exist_ok=True)
    _BUILD_META_FILE.write_text(
        json.dumps({"backend_url": backend_url, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        + "\n"
    )


def _normalize_module_name(raw: str) -> str:
    """'styled-jsx/package.json' -> 'styled-jsx'; '@swc/helpers/_/x' -> '@swc/helpers'."""
    parts = raw.split("/")
    if raw.startswith("@") and len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def _copy_traced_dependency_gap(package_name: str) -> bool:
    """Copy a package the standalone tracer missed into FRONTEND_DIST/node_modules.

    Resolves the package the same way Next's own require-hook would: relative
    to next's real installed location under pnpm's nested .pnpm/ store (and,
    cascading, relative to packages already healed into FRONTEND_DIST), rather
    than frontend/'s own node_modules (frontend/ never declared these as
    direct dependencies, so a plain require.resolve from there fails even
    though they are genuinely installed and needed at runtime).

    Some packages (notably ``client-only``) refuse ``./package.json`` via
    their ``exports`` map, so resolution falls back to the package entry and
    walks up to the directory that owns a matching package.json.

    Returns True if the package was newly copied (or already present).
    """
    node = shutil.which("node")
    if not node:
        return False

    dst_dir = FRONTEND_DIST / "node_modules" / package_name
    if dst_dir.exists():
        return True

    # Cascading anchors: next itself, then any packages already copied into
    # the assembled dist (styled-jsx is the usual parent of client-only).
    anchors: list[str] = []
    script_anchors = (
        "const anchors = [];"
        "try { anchors.push(require('path').dirname(require.resolve('next/package.json'))); } catch (e) {}"
        f"const distNm = {json.dumps(str(FRONTEND_DIST / 'node_modules'))};"
        "for (const name of ['styled-jsx', '@swc/helpers', '@next/env', 'react', 'next']) {"
        "  const candidate = require('path').join(distNm, name);"
        "  try { require('fs').accessSync(candidate); anchors.push(candidate); } catch (e) {}"
        "}"
        "console.log(JSON.stringify(anchors));"
    )
    anchor_result = subprocess.run(
        [node, "-e", script_anchors],
        cwd=FRONTEND_SRC,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if anchor_result.returncode == 0 and anchor_result.stdout.strip():
        try:
            anchors = json.loads(anchor_result.stdout.strip())
        except json.JSONDecodeError:
            anchors = []

    resolve_script = (
        "const fs = require('fs');"
        "const path = require('path');"
        f"const name = {json.dumps(package_name)};"
        f"const anchors = {json.dumps(anchors)};"
        "function resolvePkgDir(pkg, searchPaths) {"
        "  for (const anchor of searchPaths) {"
        "    try {"
        "      try {"
        "        const pkgJson = require.resolve(pkg + '/package.json', { paths: [anchor] });"
        "        return path.dirname(pkgJson);"
        "      } catch (_) {}"
        "      const entry = require.resolve(pkg, { paths: [anchor] });"
        "      let dir = path.dirname(entry);"
        "      while (dir !== path.dirname(dir)) {"
        "        const candidate = path.join(dir, 'package.json');"
        "        if (fs.existsSync(candidate)) {"
        "          try {"
        "            const meta = JSON.parse(fs.readFileSync(candidate, 'utf8'));"
        "            if (meta.name === pkg) return dir;"
        "          } catch (_) {}"
        "        }"
        "        dir = path.dirname(dir);"
        "      }"
        "    } catch (_) {}"
        "  }"
        "  return null;"
        "}"
        "const found = resolvePkgDir(name, anchors);"
        "if (!found) process.exit(1);"
        "console.log(found);"
    )
    result = subprocess.run(
        [node, "-e", resolve_script],
        cwd=FRONTEND_SRC,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    src_dir = Path(result.stdout.strip())
    if not src_dir.is_dir():
        return False
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dst_dir)
    return True


def _extract_missing_module(*blobs: str) -> Optional[str]:
    for blob in blobs:
        if not blob:
            continue
        match = _MODULE_NOT_FOUND.search(blob)
        if match:
            return _normalize_module_name(match.group(1))
    return None


def _heal_missing_standalone_modules(*, max_attempts: int = 10) -> None:
    """Iteratively detect and copy in modules the standalone tracer missed.

    Next's standalone-output tracer (@vercel/nft) has known gaps with pnpm's
    strict, non-hoisted node_modules layout. Confirmed missing modules with
    this exact frontend/pnpm-lock.yaml include styled-jsx, @swc/helpers,
    @next/env (cold boot) and client-only (first real page request via
    styled-jsx -> _document.js). A fixed one-shot list is not enough on its
    own, so:

    1. Seed the known gaps.
    2. Probe cold boot (server crash with MODULE_NOT_FOUND).
    3. Once the server stays up, issue a real GET / and heal any
       request-time MODULE_NOT_FOUND that surfaces in stderr.

    Converges once GET / returns a non-5xx response with no module-missing
    errors, or gives up quietly after max_attempts (the real run then
    surfaces whatever remains, same as before this function existed).
    """
    node = shutil.which("node")
    if not node:
        return
    server_js = FRONTEND_DIST / "server.js"
    if not server_js.exists():
        return

    for package_name in _KNOWN_TRACE_GAPS:
        _copy_traced_dependency_gap(package_name)

    seen: set[str] = set()
    for _ in range(max_attempts):
        probe_port = find_free_port()
        env = {
            **os.environ,
            "PORT": str(probe_port),
            "HOSTNAME": "127.0.0.1",
            "NEXT_TELEMETRY_DISABLED": "1",
        }
        proc = subprocess.Popen(
            [node, str(server_js)],
            cwd=FRONTEND_DIST,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            # Cold-boot window: if it dies immediately, heal from its output.
            try:
                out, _ = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                out = ""
            else:
                missing = _extract_missing_module(out or "")
                if missing and missing not in seen:
                    seen.add(missing)
                    _copy_traced_dependency_gap(missing)
                    continue
                # Crashed for another reason; not our job.
                return

            # Still running: issue a real page request so request-time
            # require() paths (e.g. styled-jsx -> client-only) fire.
            request_error = ""
            try:
                import urllib.error
                import urllib.request

                with urllib.request.urlopen(f"http://127.0.0.1:{probe_port}/", timeout=5) as resp:
                    status = getattr(resp, "status", 200)
                    if status < 500:
                        # Drain any late MODULE_NOT_FOUND lines, then succeed.
                        time.sleep(0.4)
                        return
            except Exception as exc:
                request_error = str(exc)

            # Kill and read whatever the server logged during the request.
            proc.terminate()
            try:
                out2, _ = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                out2, _ = proc.communicate(timeout=3)
            missing = _extract_missing_module(out or "", out2 or "", request_error)
            if missing and missing not in seen:
                seen.add(missing)
                _copy_traced_dependency_gap(missing)
                continue
            return
        finally:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.communicate(timeout=3)
                except Exception:
                    pass


def _copy_next_middleware_into_dist(next_dir: Path, dest: Path) -> None:
    """Copy Edge middleware into the assembled standalone dist.

    ``.next/standalone`` does not include ``server/src/middleware.js``. Without
    those files, ``keprix dashboard`` serves the marketing homepage at ``/``
    instead of redirecting localhost to ``/home``.
    """
    server_src = next_dir / "server"
    server_dst = dest / ".next" / "server"
    for rel in (
        Path("src") / "middleware.js",
        Path("src") / "middleware.js.map",
        Path("edge-runtime-webpack.js"),
        Path("edge-runtime-webpack.js.map"),
        Path("middleware-manifest.json"),
    ):
        src = server_src / rel
        if not src.is_file():
            continue
        dst = server_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def assemble_standalone_dist(*, backend_url: Optional[str] = None) -> None:
    """Copy the Next.js standalone build output into FRONTEND_DIST.

    Replicates docker/Dockerfile.frontend's runner stage COPY steps exactly:
    .next/standalone becomes the app root, .next/static and public/ are
    copied in alongside it, and ui/design-system + CHANGELOG.md are copied
    one level up (matching /app/ui/design-system and /app/CHANGELOG.md
    relative to Docker's /app/frontend app root).
    """
    next_dir = FRONTEND_SRC / ".next"
    standalone = next_dir / "standalone"
    if not standalone.exists():
        raise FileNotFoundError(
            f'next build did not produce {standalone} (output: "standalone" missing from next.config.ts?)'
        )

    if FRONTEND_DIST.exists():
        shutil.rmtree(FRONTEND_DIST)
    shutil.copytree(standalone, FRONTEND_DIST)

    static_src = next_dir / "static"
    if static_src.exists():
        shutil.copytree(static_src, FRONTEND_DIST / ".next" / "static", dirs_exist_ok=True)

    public_src = FRONTEND_SRC / "public"
    if public_src.exists():
        shutil.copytree(public_src, FRONTEND_DIST / "public", dirs_exist_ok=True)

    design_system_src = REPO_ROOT / "ui" / "design-system"
    if design_system_src.exists():
        design_system_dst = FRONTEND_DIST.parent / "ui" / "design-system"
        if design_system_dst.exists():
            shutil.rmtree(design_system_dst)
        shutil.copytree(design_system_src, design_system_dst)

    changelog_src = REPO_ROOT / "CHANGELOG.md"
    if changelog_src.exists():
        shutil.copy2(changelog_src, FRONTEND_DIST.parent / "CHANGELOG.md")

    _copy_next_middleware_into_dist(next_dir, FRONTEND_DIST)

    if not (FRONTEND_DIST / "server.js").exists():
        raise FileNotFoundError(
            f"Assembled dist at {FRONTEND_DIST} but no server.js found inside; "
            "unexpected .next/standalone layout, check the Next.js version's output shape."
        )

    _heal_missing_standalone_modules()

    if backend_url:
        _write_build_meta(backend_url)


def build_frontend_standalone(*, backend_url: str, fatal: bool = False) -> bool:
    """Build the standalone Next.js dashboard frontend if pnpm is available.

    ``backend_url`` is baked into Next.js rewrites at build time (same contract
    as docker/Dockerfile.frontend's ``BACKEND_REWRITE_URL`` build ARG). A
    dist built for one backend URL cannot correctly proxy ``/api/*`` to a
    different backend port.

    Mirrors main.py's ``_build_web_ui()`` in structure and message style.
    Returns True if the build succeeded, was skipped (no frontend/ source;
    e.g. a non-editable pipx/PyPI install), or wasn't needed.
    """
    if not frontend_source_available():
        if fatal:
            _say("No frontend/ source found; this install has no dashboard frontend to build.")
            _say("This is expected for a plain `pipx install '.[tui]' --force` (non-editable) install:")
            _say("only an editable/source-checkout install (scripts/install.sh, or")
            _say("`pipx install -e '.[tui]' --force`) has frontend/ available at runtime.")
            _say("Alternatively, use the Docker stack:  docker compose -f docker/docker-compose.yml up -d --build")
        return not fatal

    if not _frontend_build_needed(backend_url):
        return True

    pnpm = shutil.which("pnpm")
    if not pnpm:
        if _backend_url_mismatch(backend_url):
            _say("pnpm is not on PATH; cannot rebuild the dashboard frontend for this backend URL.")
            _say("  The existing dist still proxies /api to a different port, so login/setup will fail.")
            _say("  Install pnpm (corepack enable && corepack prepare pnpm@9.15.0 --activate), then:")
            _say(f"  cd frontend && BACKEND_REWRITE_URL={backend_url} pnpm exec next build")
            return False
        if fatal:
            _say("Dashboard frontend not built and pnpm is not available.")
            _say("Install Node.js + pnpm (corepack enable && corepack prepare pnpm@9.15.0 --activate), then run:")
            _say("  cd frontend && pnpm install --frozen-lockfile && pnpm exec next build")
        return not fatal

    _say(f"→ Building dashboard frontend (Next.js standalone; rewrite → {backend_url})...")

    from keprix_cli.main import _run_with_idle_timeout  # local import: avoid a main.py <-> frontend_standalone.py import cycle

    def _relay(result: "subprocess.CompletedProcess") -> None:
        for blob in (getattr(result, "stdout", None), getattr(result, "stderr", None)):
            if not blob:
                continue
            text = blob.decode("utf-8", errors="replace").rstrip() if isinstance(blob, bytes) else blob.rstrip()
            if text:
                _say(text)

    r1 = subprocess.run(
        [pnpm, "install", "--frozen-lockfile"],
        cwd=FRONTEND_SRC,
        capture_output=True,
        timeout=300,
    )
    if r1.returncode != 0:
        _say(f"  {'✗' if fatal else '⚠'} pnpm install failed" + ("" if fatal else " (dashboard web UI will not be available)"))
        _relay(r1)
        if fatal:
            _say("  Run manually:  cd frontend && pnpm install --frozen-lockfile")
        return False

    build_env = {
        **os.environ,
        "BACKEND_REWRITE_URL": backend_url,
        # Keep browser same-origin /api (rewrites handle the proxy), matching Docker.
        "NEXT_PUBLIC_API_URL": "",
        "NEXT_PUBLIC_CE_API_URL": "",
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    r2 = _run_with_idle_timeout([pnpm, "exec", "next", "build"], cwd=FRONTEND_SRC, env=build_env)
    if r2.returncode != 0:
        time.sleep(3)
        r2 = _run_with_idle_timeout([pnpm, "exec", "next", "build"], cwd=FRONTEND_SRC, env=build_env)

    if r2.returncode != 0:
        build_output = (getattr(r2, "stderr", "") or "") + (getattr(r2, "stdout", "") or "")
        stderr_tail = "\n  ".join(build_output.strip().splitlines()[-10:]) if build_output.strip() else ""
        if (FRONTEND_DIST / "server.js").exists() and not _backend_url_mismatch(backend_url):
            _say("  ⚠ Dashboard frontend build failed; serving stale dist as fallback")
            if stderr_tail:
                _say(f"  Build error:\n  {stderr_tail}")
            return True
        _say(f"  {'✗' if fatal else '⚠'} Dashboard frontend build failed" + ("" if fatal else " (dashboard web UI will not be available)"))
        if _backend_url_mismatch(backend_url):
            _say("  Existing dist proxies /api to a different backend; refusing to serve it.")
        if stderr_tail:
            _say(f"  {stderr_tail}")
        if fatal:
            _say("  Run manually:  cd frontend && BACKEND_REWRITE_URL=... pnpm exec next build")
        return False

    try:
        assemble_standalone_dist(backend_url=backend_url)
    except Exception as exc:
        _say(f"  {'✗' if fatal else '⚠'} Failed to assemble the standalone dist: {exc}")
        return not fatal

    _say("  ✓ Dashboard frontend built")
    return True


def find_free_port(host: str = "127.0.0.1") -> int:
    """Bind to port 0, read the OS-assigned free port, and release it.

    Same TOCTOU tradeoff web_server.py's own ephemeral-port comments already
    accept for the backend; acceptable for a short-lived local spawn.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _resolve_frontend_port(host: str) -> int:
    """Use ``KEPRIX_DASHBOARD_FRONTEND_PORT`` when set; otherwise pick a free port.

    The persistent ``keprix dashboard install`` unit pins this so the UI URL
    stays stable across restarts. Foreground ``keprix dashboard`` leaves it
    unset and keeps the historical ephemeral bind.
    """
    raw = os.environ.get("KEPRIX_DASHBOARD_FRONTEND_PORT", "").strip()
    if raw.isdigit():
        port = int(raw)
        if 1 <= port <= 65535:
            return port
    return find_free_port(host)


def spawn_frontend_server(*, host: str, backend_port: int) -> "tuple[subprocess.Popen, int]":
    """Launch the standalone Next.js server as a managed child process.

    Returns (process, frontend_port). Uses an absolute path to server.js
    (not a relative arg) so the child's command line is distinguishable for
    stale-process cleanup (main.py's _find_stale_dashboard_pids).

    Note: ``BACKEND_REWRITE_URL`` is set here for documentation/parity with
    Docker's runtime env, but Next.js has already baked rewrites at build
    time. Callers must pass a matching ``backend_url`` into
    ``build_frontend_standalone`` so the baked rewrite target equals the
    live backend port.
    """
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError(
            "node executable not found on PATH; Node.js is required to run the built dashboard frontend"
        )

    frontend_port = _resolve_frontend_port(host)
    server_js = str((FRONTEND_DIST / "server.js").resolve())

    from keprix_constants import get_keprix_home

    log_dir = get_keprix_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "frontend-dashboard.log"
    log_file = open(log_path, "ab", buffering=0)
    log_file.write(
        f"\n=== frontend dashboard started {time.strftime('%Y-%m-%d %H:%M:%S')} (port {frontend_port}) ===\n".encode()
    )

    env = {
        **os.environ,
        "PORT": str(frontend_port),
        "HOSTNAME": host,
        "BACKEND_REWRITE_URL": f"http://{host}:{backend_port}",
        "NEXT_TELEMETRY_DISABLED": "1",
    }

    popen_kwargs: dict = {
        "cwd": str(FRONTEND_DIST),
        "stdin": subprocess.DEVNULL,
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
        "env": env,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen([node, server_js], **popen_kwargs)
    log_file.close()
    return proc, frontend_port


def wait_for_frontend_ready(host: str, port: int, proc: "subprocess.Popen", timeout: float = 30.0) -> bool:
    """Poll the frontend until it responds, or the child exits, or timeout."""
    import httpx

    deadline = time.monotonic() + timeout
    url = f"http://{host}:{port}/"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with httpx.Client(timeout=httpx.Timeout(2.0)) as client:
                resp = client.get(url)
            if resp.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def terminate_frontend_server(proc: Optional["subprocess.Popen"], timeout: float = 5.0) -> None:
    """Gracefully stop the frontend child process: SIGTERM, wait, then SIGKILL."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5.0)
        except Exception:
            pass
    except Exception:
        pass
