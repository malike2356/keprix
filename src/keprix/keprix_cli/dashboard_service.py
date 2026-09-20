"""Persistent dashboard service (systemd user unit / launchd).

Sibling of ``keprix gateway install``. ``keprix dashboard`` remains the
foreground launcher; this module writes a supervised unit that runs::

    python -m keprix_cli.main dashboard --host 127.0.0.1 --port 9119 --no-open

The unit pins ``KEPRIX_DASHBOARD_FRONTEND_PORT`` so the UI URL stays stable
across restarts, and ``KEPRIX_DASHBOARD_SERVICE=1`` so the service never
tries to open a browser.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from keprix_cli.config import get_keprix_home, is_managed, managed_error
from keprix_cli.gateway import (
    PROJECT_ROOT,
    SystemScopeRequiresRootError,
    UserSystemdUnavailableError,
    _build_service_path_dirs,
    _build_user_local_paths,
    _build_wsl_interop_paths,
    _detect_venv_dir,
    _ensure_linger_enabled,
    _keprix_home_for_target_user,
    _normalize_service_definition,
    _preflight_user_systemd,
    _profile_arg,
    _profile_arg_for_target_user,
    _profile_suffix,
    _remap_path_for_user,
    _run_systemctl,
    _service_scope_label,
    _stable_service_working_dir,
    _strip_optional_systemd_directives,
    _system_service_identity,
    _temp_home_in_service_definition,
    get_python_path,
    is_linux,
    is_macos,
    is_windows,
    is_wsl,
    supports_systemd_services,
)
from keprix_constants import is_container, is_termux

SERVICE_BASE = "keprix-dashboard"
SERVICE_DESCRIPTION = "Keprix Dashboard - local web UI"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 9119
DEFAULT_FRONTEND_PORT = 9120


def get_service_name() -> str:
    suffix = _profile_suffix()
    if not suffix:
        return SERVICE_BASE
    return f"{SERVICE_BASE}-{suffix}"


def get_systemd_unit_path(system: bool = False) -> Path:
    name = get_service_name()
    if system:
        return Path("/etc/systemd/system") / f"{name}.service"
    return Path.home() / ".config" / "systemd" / "user" / f"{name}.service"


def get_launchd_label() -> str:
    suffix = _profile_suffix()
    return f"ai.keprix.dashboard-{suffix}" if suffix else "ai.keprix.dashboard"


def get_launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{get_launchd_label()}.plist"


def _default_frontend_port(backend_port: int) -> int:
    if backend_port == DEFAULT_BACKEND_PORT:
        return DEFAULT_FRONTEND_PORT
    return backend_port + 1


def _host_port_from_unit(text: str) -> tuple[str, int, int]:
    host = DEFAULT_HOST
    port = DEFAULT_BACKEND_PORT
    frontend_port = DEFAULT_FRONTEND_PORT
    m = re.search(r"--host\s+(\S+)", text)
    if m:
        host = m.group(1).strip().strip('"')
    m = re.search(r"--port\s+(\d+)", text)
    if m:
        port = int(m.group(1))
    m = re.search(r"KEPRIX_DASHBOARD_FRONTEND_PORT=(\d+)", text)
    if m:
        frontend_port = int(m.group(1))
    else:
        frontend_port = _default_frontend_port(port)
    return host, port, frontend_port


def _require_root(action: str) -> None:
    if os.geteuid() != 0:  # windows-footgun: ok — POSIX systemd helper
        raise SystemScopeRequiresRootError(
            f"System dashboard {action} requires root. Re-run with sudo.",
            action,
        )


def _refuse_temp_home(definition: str, kind: str) -> bool:
    temp_home = _temp_home_in_service_definition(definition)
    if temp_home is None:
        return False
    print(
        f"✗ Refusing to write the dashboard {kind}: KEPRIX_HOME resolves to a "
        f"temporary directory ({temp_home})."
    )
    print(
        "  Unset KEPRIX_HOME (or run from a clean shell) and retry."
    )
    return True


def generate_systemd_unit(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_BACKEND_PORT,
    frontend_port: int = DEFAULT_FRONTEND_PORT,
    system: bool = False,
    run_as_user: str | None = None,
) -> str:
    python_path = get_python_path()
    working_dir = _stable_service_working_dir()
    detected_venv = _detect_venv_dir()
    venv_dir = str(detected_venv) if detected_venv else str(PROJECT_ROOT / "venv")

    path_entries = _build_service_path_dirs()
    resolved_node = shutil.which("node")
    if resolved_node:
        resolved_node_dir = str(Path(resolved_node).resolve().parent)
        if resolved_node_dir not in path_entries:
            path_entries.append(resolved_node_dir)

    common_bin_paths = [
        "/usr/local/sbin",
        "/usr/local/bin",
        "/usr/sbin",
        "/usr/bin",
        "/sbin",
        "/bin",
    ]

    exec_tail = (
        f"dashboard --host {host} --port {port} --no-open"
    )

    if system:
        username, group_name, home_dir = _system_service_identity(run_as_user)
        keprix_home = _keprix_home_for_target_user(home_dir)
        profile_arg = _profile_arg_for_target_user(keprix_home, home_dir)
        python_path = _remap_path_for_user(python_path, home_dir)
        working_dir = str(keprix_home) if keprix_home else _remap_path_for_user(
            working_dir, home_dir
        )
        venv_dir = _remap_path_for_user(venv_dir, home_dir)
        path_entries = [_remap_path_for_user(p, home_dir) for p in path_entries]
        path_entries.extend(_build_user_local_paths(Path(home_dir), path_entries))
        path_entries.extend(_build_wsl_interop_paths(path_entries))
        path_entries.extend(common_bin_paths)
        sane_path = ":".join(path_entries)
        profile_bit = f" {profile_arg}" if profile_arg else ""
        return f"""[Unit]
Description={SERVICE_DESCRIPTION}
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User={username}
Group={group_name}
ExecStart={python_path} -m keprix_cli.main{profile_bit} {exec_tail}
WorkingDirectory={working_dir}
Environment="HOME={home_dir}"
Environment="USER={username}"
Environment="LOGNAME={username}"
Environment="PATH={sane_path}"
Environment="VIRTUAL_ENV={venv_dir}"
Environment="KEPRIX_HOME={keprix_home}"
Environment="KEPRIX_DASHBOARD_SERVICE=1"
Environment="KEPRIX_DASHBOARD_FRONTEND_PORT={frontend_port}"
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    keprix_home = str(get_keprix_home().resolve())
    profile_arg = _profile_arg(keprix_home)
    path_entries.extend(_build_user_local_paths(Path.home(), path_entries))
    path_entries.extend(_build_wsl_interop_paths(path_entries))
    path_entries.extend(common_bin_paths)
    sane_path = ":".join(path_entries)
    profile_bit = f" {profile_arg}" if profile_arg else ""
    return f"""[Unit]
Description={SERVICE_DESCRIPTION}
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart={python_path} -m keprix_cli.main{profile_bit} {exec_tail}
WorkingDirectory={working_dir}
Environment="PATH={sane_path}"
Environment="VIRTUAL_ENV={venv_dir}"
Environment="KEPRIX_HOME={keprix_home}"
Environment="KEPRIX_DASHBOARD_SERVICE=1"
Environment="KEPRIX_DASHBOARD_FRONTEND_PORT={frontend_port}"
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""


def systemd_unit_is_current(
    system: bool = False,
    *,
    host: str | None = None,
    port: int | None = None,
    frontend_port: int | None = None,
) -> bool:
    unit_path = get_systemd_unit_path(system=system)
    if not unit_path.exists():
        return False
    installed = unit_path.read_text(encoding="utf-8")
    inst_host, inst_port, inst_fe = _host_port_from_unit(installed)
    expected = generate_systemd_unit(
        host=host or inst_host,
        port=port if port is not None else inst_port,
        frontend_port=frontend_port if frontend_port is not None else inst_fe,
        system=system,
    )
    return _normalize_service_definition(
        _strip_optional_systemd_directives(installed)
    ) == _normalize_service_definition(_strip_optional_systemd_directives(expected))


def generate_launchd_plist(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_BACKEND_PORT,
    frontend_port: int = DEFAULT_FRONTEND_PORT,
) -> str:
    python_path = get_python_path()
    working_dir = _stable_service_working_dir()
    keprix_home = str(get_keprix_home().resolve())
    log_dir = get_keprix_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    label = get_launchd_label()
    profile_arg = _profile_arg(keprix_home)
    detected_venv = _detect_venv_dir()
    venv_dir = str(detected_venv) if detected_venv else str(PROJECT_ROOT / "venv")
    priority_dirs = _build_service_path_dirs()
    resolved_node = shutil.which("node")
    if resolved_node:
        resolved_node_dir = str(Path(resolved_node).resolve().parent)
        if resolved_node_dir not in priority_dirs:
            priority_dirs.append(resolved_node_dir)
    sane_path = ":".join(
        dict.fromkeys(
            priority_dirs + [p for p in os.environ.get("PATH", "").split(":") if p]
        )
    )
    prog_args = [
        f"<string>{python_path}</string>",
        "<string>-m</string>",
        "<string>keprix_cli.main</string>",
    ]
    if profile_arg:
        for part in profile_arg.split():
            prog_args.append(f"<string>{part}</string>")
    prog_args.extend(
        [
            "<string>dashboard</string>",
            "<string>--host</string>",
            f"<string>{host}</string>",
            "<string>--port</string>",
            f"<string>{port}</string>",
            "<string>--no-open</string>",
        ]
    )
    prog_args_xml = "\n        ".join(prog_args)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        {prog_args_xml}
    </array>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{sane_path}</string>
        <key>VIRTUAL_ENV</key>
        <string>{venv_dir}</string>
        <key>KEPRIX_HOME</key>
        <string>{keprix_home}</string>
        <key>KEPRIX_DASHBOARD_SERVICE</key>
        <string>1</string>
        <key>KEPRIX_DASHBOARD_FRONTEND_PORT</key>
        <string>{frontend_port}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir / "dashboard.log"}</string>
    <key>StandardErrorPath</key>
    <string>{log_dir / "dashboard.error.log"}</string>
</dict>
</plist>
"""


def _ensure_frontend_dist(host: str, port: int) -> None:
    try:
        from keprix_cli import frontend_standalone as _fe
    except Exception as exc:
        print(f"⚠ Could not import dashboard frontend builder: {exc}")
        return
    backend_url = f"http://{host}:{port}"
    dist = _fe.FRONTEND_DIST / "server.js"
    if dist.exists() and _fe.frontend_dist_matches_backend(backend_url):
        return
    print("→ Building dashboard frontend for the service (one-time)...")
    try:
        ok = _fe.build_frontend_standalone(backend_url=backend_url, fatal=False)
    except Exception as exc:
        print(f"⚠ Frontend build failed: {exc}")
        return
    if not ok:
        print("⚠ Frontend build failed; the service will start the API without the web UI.")


def _stop_stray_dashboards() -> None:
    try:
        from keprix_cli.main import _kill_stale_dashboard_processes

        _kill_stale_dashboard_processes(
            reason="freeing the port for the dashboard service"
        )
    except Exception:
        pass


def _require_installed(action: str, system: bool = False) -> None:
    unit_path = get_systemd_unit_path(system=system)
    if not unit_path.exists():
        scope_flag = " --system" if system else ""
        print("✗ Dashboard service is not installed")
        print(f"  Run: {'sudo ' if system else ''}keprix dashboard install{scope_flag}")
        sys.exit(1)


def _refresh_unit_if_needed(system: bool = False) -> None:
    unit_path = get_systemd_unit_path(system=system)
    if not unit_path.exists() or systemd_unit_is_current(system=system):
        return
    installed = unit_path.read_text(encoding="utf-8")
    host, port, frontend_port = _host_port_from_unit(installed)
    new_unit = generate_systemd_unit(
        host=host, port=port, frontend_port=frontend_port, system=system
    )
    if _refuse_temp_home(new_unit, "systemd unit"):
        return
    print(f"↻ Updating dashboard service definition at: {unit_path}")
    unit_path.write_text(new_unit, encoding="utf-8")
    _run_systemctl(["daemon-reload"], system=system, check=True, timeout=30)


def systemd_install(
    *,
    force: bool = False,
    system: bool = False,
    run_as_user: str | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_BACKEND_PORT,
    frontend_port: int = DEFAULT_FRONTEND_PORT,
    start_now: bool = True,
) -> None:
    if system:
        _require_root("install")

    unit_path = get_systemd_unit_path(system=system)
    scope_flag = " --system" if system else ""
    new_unit = generate_systemd_unit(
        host=host,
        port=port,
        frontend_port=frontend_port,
        system=system,
        run_as_user=run_as_user,
    )
    if _refuse_temp_home(new_unit, "systemd unit"):
        sys.exit(1)

    if unit_path.exists() and not force:
        if not systemd_unit_is_current(
            system=system, host=host, port=port, frontend_port=frontend_port
        ):
            print(
                f"↻ Repairing outdated {_service_scope_label(system)} dashboard "
                f"service at: {unit_path}"
            )
            unit_path.write_text(new_unit, encoding="utf-8")
            _run_systemctl(["daemon-reload"], system=system, check=True, timeout=30)
            _run_systemctl(
                ["enable", get_service_name()], system=system, check=True, timeout=30
            )
            print("✓ Dashboard service definition updated")
            _ensure_frontend_dist(host, port)
            if start_now:
                systemd_start(system=system)
            return
        print(f"Service already installed at: {unit_path}")
        print("Use --force to reinstall")
        return

    _ensure_frontend_dist(host, port)
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Installing {_service_scope_label(system)} dashboard service to: {unit_path}")
    unit_path.write_text(new_unit, encoding="utf-8")
    _run_systemctl(["daemon-reload"], system=system, check=True, timeout=30)
    _run_systemctl(["enable", get_service_name()], system=system, check=True, timeout=30)

    print()
    print(f"✓ {_service_scope_label(system).capitalize()} dashboard service installed and enabled")
    print()
    print(f"  Web UI  → http://{host}:{frontend_port}/home")
    print(f"  Backend → http://{host}:{port}")
    print()
    print("Next steps:")
    print(f"  {'sudo ' if system else ''}keprix dashboard start{scope_flag}")
    print(f"  {'sudo ' if system else ''}keprix dashboard status{scope_flag}")
    print(
        f"  {'journalctl' if system else 'journalctl --user'} -u {get_service_name()} -f"
    )
    print()
    if not system:
        _ensure_linger_enabled()

    if start_now:
        systemd_start(system=system)


def systemd_uninstall(system: bool = False) -> None:
    if system:
        _require_root("uninstall")
    _run_systemctl(["stop", get_service_name()], system=system, check=False, timeout=90)
    _run_systemctl(
        ["disable", get_service_name()], system=system, check=False, timeout=30
    )
    unit_path = get_systemd_unit_path(system=system)
    if unit_path.exists():
        unit_path.unlink()
        print(f"✓ Removed {unit_path}")
    _run_systemctl(["daemon-reload"], system=system, check=True, timeout=30)
    print(f"✓ {_service_scope_label(system).capitalize()} dashboard service uninstalled")


def systemd_start(system: bool = False) -> None:
    if system:
        _require_root("start")
    else:
        _preflight_user_systemd()
    _require_installed("start", system=system)
    _refresh_unit_if_needed(system=system)
    _stop_stray_dashboards()
    _run_systemctl(["start", get_service_name()], system=system, check=True, timeout=30)
    unit = get_systemd_unit_path(system=system).read_text(encoding="utf-8")
    host, port, frontend_port = _host_port_from_unit(unit)
    print(f"✓ {_service_scope_label(system).capitalize()} dashboard service started")
    print(f"  Web UI  → http://{host}:{frontend_port}/home")
    print(f"  Backend → http://{host}:{port}")


def systemd_stop(system: bool = False) -> None:
    if system:
        _require_root("stop")
    _require_installed("stop", system=system)
    _run_systemctl(["stop", get_service_name()], system=system, check=True, timeout=90)
    print(f"✓ {_service_scope_label(system).capitalize()} dashboard service stopped")


def systemd_restart(system: bool = False) -> None:
    if system:
        _require_root("restart")
    else:
        _preflight_user_systemd()
    _require_installed("restart", system=system)
    _run_systemctl(
        ["reset-failed", get_service_name()],
        system=system,
        check=False,
        timeout=30,
    )
    _run_systemctl(["restart", get_service_name()], system=system, check=True, timeout=90)
    print(f"✓ {_service_scope_label(system).capitalize()} dashboard service restarted")


def systemd_status(system: bool = False) -> None:
    unit_path = get_systemd_unit_path(system=system)
    scope_flag = " --system" if system else ""
    if not unit_path.exists():
        print("✗ Dashboard service is not installed")
        print(f"  Run: {'sudo ' if system else ''}keprix dashboard install{scope_flag}")
        return
    _run_systemctl(
        ["status", get_service_name(), "--no-pager"],
        system=system,
        capture_output=False,
        timeout=10,
    )


def _launchd_domain() -> str:
    return f"gui/{os.getuid()}"  # windows-footgun: ok — macOS launchd


def launchd_install(
    *,
    force: bool = False,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_BACKEND_PORT,
    frontend_port: int = DEFAULT_FRONTEND_PORT,
    start_now: bool = True,
) -> None:
    plist_path = get_launchd_plist_path()
    new_plist = generate_launchd_plist(
        host=host, port=port, frontend_port=frontend_port
    )
    if _refuse_temp_home(new_plist, "launchd plist"):
        sys.exit(1)
    if plist_path.exists() and not force:
        print(f"Service already installed at: {plist_path}")
        print("Use --force to reinstall")
        return
    _ensure_frontend_dist(host, port)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Installing launchd service to: {plist_path}")
    plist_path.write_text(new_plist, encoding="utf-8")
    subprocess.run(
        ["launchctl", "bootstrap", _launchd_domain(), str(plist_path)],
        check=False,
        timeout=30,
    )
    print()
    print("✓ Dashboard service installed")
    print(f"  Web UI  → http://{host}:{frontend_port}/home")
    print(f"  Backend → http://{host}:{port}")
    if start_now:
        launchd_start()


def launchd_uninstall() -> None:
    plist_path = get_launchd_plist_path()
    label = get_launchd_label()
    subprocess.run(
        ["launchctl", "bootout", f"{_launchd_domain()}/{label}"],
        check=False,
        timeout=90,
    )
    if plist_path.exists():
        plist_path.unlink()
        print(f"✓ Removed {plist_path}")
    print("✓ Dashboard service uninstalled")


def launchd_start() -> None:
    label = get_launchd_label()
    plist_path = get_launchd_plist_path()
    if not plist_path.exists():
        print("✗ Dashboard service is not installed")
        print("  Run: keprix dashboard install")
        sys.exit(1)
    _stop_stray_dashboards()
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"{_launchd_domain()}/{label}"],
        check=False,
        timeout=30,
    )
    print("✓ Dashboard service started")


def launchd_stop() -> None:
    label = get_launchd_label()
    subprocess.run(
        ["launchctl", "kill", "SIGTERM", f"{_launchd_domain()}/{label}"],
        check=False,
        timeout=30,
    )
    print("✓ Dashboard service stopped")


def launchd_restart() -> None:
    launchd_stop()
    launchd_start()


def launchd_status() -> None:
    label = get_launchd_label()
    result = subprocess.run(
        ["launchctl", "print", f"{_launchd_domain()}/{label}"],
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        print("✗ Dashboard service is not loaded")
        print("  Run: keprix dashboard install")


def dashboard_service_command(args) -> None:
    subcmd = getattr(args, "dashboard_subcommand", None)
    try:
        _dispatch(subcmd, args)
    except UserSystemdUnavailableError as e:
        print("User systemd not reachable:")
        for line in str(e).splitlines():
            print(f"  {line}")
        sys.exit(1)
    except SystemScopeRequiresRootError as e:
        print(str(e))
        sys.exit(1)


def _dispatch(subcmd: str | None, args) -> None:
    if is_managed():
        managed_error(f"{subcmd or 'manage'} dashboard service (managed by NixOS)")
        return

    system = bool(getattr(args, "system", False))
    host = getattr(args, "host", None) or DEFAULT_HOST
    port = int(getattr(args, "port", None) or DEFAULT_BACKEND_PORT)
    frontend_port = int(
        getattr(args, "frontend_port", None) or _default_frontend_port(port)
    )

    if subcmd == "install":
        _dispatch_install(
            force=bool(getattr(args, "force", False)),
            system=system,
            run_as_user=getattr(args, "run_as_user", None),
            host=host,
            port=port,
            frontend_port=frontend_port,
            start_now=not bool(getattr(args, "no_start", False)),
        )
        return
    if subcmd == "uninstall":
        _dispatch_lifecycle("uninstall", system)
        return
    if subcmd == "start":
        _dispatch_lifecycle("start", system)
        return
    if subcmd == "stop":
        _dispatch_lifecycle("stop", system)
        return
    if subcmd == "restart":
        _dispatch_lifecycle("restart", system)
        return
    if subcmd == "status":
        _dispatch_lifecycle("status", system)
        return
    print(f"Unknown dashboard service command: {subcmd}")
    sys.exit(2)


def _dispatch_install(
    *,
    force: bool,
    system: bool,
    run_as_user: str | None,
    host: str,
    port: int,
    frontend_port: int,
    start_now: bool,
) -> None:
    if is_termux():
        print("Dashboard service installation is not supported on Termux.")
        print("Run in the foreground: keprix dashboard")
        sys.exit(1)
    if supports_systemd_services():
        if is_wsl():
            print("WSL detected — systemd user services may not survive WSL restarts.")
            print()
        systemd_install(
            force=force,
            system=system,
            run_as_user=run_as_user,
            host=host,
            port=port,
            frontend_port=frontend_port,
            start_now=start_now,
        )
        return
    if is_macos():
        launchd_install(
            force=force,
            host=host,
            port=port,
            frontend_port=frontend_port,
            start_now=start_now,
        )
        return
    if is_windows():
        print("Dashboard service install is not supported on Windows yet.")
        print("Keep a dedicated terminal open, or run: keprix dashboard --no-open")
        sys.exit(1)
    if is_container():
        from keprix_cli.service_manager import detect_service_manager

        if detect_service_manager() == "s6":
            print("In the Keprix container the dashboard is supervised when")
            print("KEPRIX_DASHBOARD=1 is set on the container. No host unit needed.")
            sys.exit(0)
        print("Service installation is not needed inside a Docker container.")
        print("Use the container restart policy, or set KEPRIX_DASHBOARD=1.")
        sys.exit(0)
    print("Dashboard service installation is not supported on this platform.")
    print("Run in the foreground: keprix dashboard")
    sys.exit(1)


def _dispatch_lifecycle(action: str, system: bool) -> None:
    if is_termux():
        print(f"Dashboard service {action} is not supported on Termux.")
        sys.exit(1)
    if supports_systemd_services():
        {
            "uninstall": systemd_uninstall,
            "start": systemd_start,
            "stop": systemd_stop,
            "restart": systemd_restart,
            "status": systemd_status,
        }[action](system=system)
        return
    if is_macos():
        {
            "uninstall": launchd_uninstall,
            "start": launchd_start,
            "stop": launchd_stop,
            "restart": launchd_restart,
            "status": launchd_status,
        }[action]()
        return
    print(f"Dashboard service {action} is not supported on this platform.")
    sys.exit(1)
