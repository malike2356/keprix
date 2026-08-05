"""Platform detection for keprix TUI.

Detects OS, shell, and provides platform-adaptive helpers for
paths, browser opening, and clipboard commands.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class PlatformInfo:
    """Detected platform information."""

    os_name: str            # "linux", "darwin", "windows", "android"
    os_release: str         # e.g. "Linux Mint 22", "macOS 15"
    arch: str               # "x86_64", "aarch64"
    shell: str              # "bash", "zsh", "fish", "pwsh", "cmd"
    is_termux: bool
    is_wsl: bool
    is_ci: bool
    has_display: bool       # X11/Wayland display available


@lru_cache(maxsize=1)
def get_platform_info() -> PlatformInfo:
    """Detect and return platform information (cached)."""
    return _detect_platform()


def _detect_platform() -> PlatformInfo:
    system = platform.system().lower()

    if system == "linux":
        if os.environ.get("TERMUX_VERSION"):
            os_name = "android"
            is_termux = True
        elif "microsoft" in platform.release().lower() or "wsl" in platform.release().lower():
            os_name = "linux"
            is_termux = False
        else:
            os_name = "linux"
            is_termux = False
    elif system == "darwin":
        os_name = "darwin"
        is_termux = False
    elif system == "windows":
        os_name = "windows"
        is_termux = False
    else:
        os_name = system
        is_termux = False

    # OS release
    try:
        if os_name == "linux":
            os_release = _linux_release()
        elif os_name == "darwin":
            os_release = f"macOS {platform.mac_ver()[0]}"
        elif os_name == "windows":
            os_release = platform.release()
        else:
            os_release = platform.release()
    except Exception:
        os_release = platform.release()

    # Shell detection
    shell = os.environ.get("SHELL", "")
    shell_name = os.path.basename(shell) if shell else ""
    if not shell_name:
        if os_name == "windows":
            if os.environ.get("PSModulePath"):
                shell_name = "pwsh"
            else:
                shell_name = "cmd"
        else:
            shell_name = "sh"

    # WSL detection
    is_wsl = "microsoft" in platform.release().lower()

    # CI detection
    is_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))

    # Display check
    has_display = bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or (os_name == "darwin")  # macOS always has display
        or (os_name == "windows")
    )

    return PlatformInfo(
        os_name=os_name,
        os_release=os_release,
        arch=platform.machine(),
        shell=shell_name,
        is_termux=is_termux,
        is_wsl=is_wsl,
        is_ci=is_ci,
        has_display=has_display,
    )


def _linux_release() -> str:
    """Try to read the Linux distribution name."""
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "Linux"


def open_url(url: str) -> None:
    """Open a URL in the system browser."""
    pi = get_platform_info()
    if pi.os_name == "darwin":
        os.system(f"open '{url}'")
    elif pi.os_name == "windows":
        os.system(f"start '{url}'")
    else:
        os.system(f"xdg-open '{url}' > /dev/null 2>&1 &")


def clipboard_copy_command() -> str | None:
    """Return the best clipboard copy command for this platform."""
    pi = get_platform_info()
    if pi.os_name == "darwin":
        return "pbcopy"
    if pi.os_name == "windows":
        return "clip"
    # Linux: prefer wl-copy on Wayland, xclip/xsel on X11
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wl-copy"
    for cmd in ("xclip -selection clipboard", "xsel --clipboard --input"):
        if _command_exists(cmd.split()[0]):
            return cmd
    return None


def clipboard_paste_command() -> str | None:
    """Return the best clipboard paste command for this platform."""
    pi = get_platform_info()
    if pi.os_name == "darwin":
        return "pbpaste"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wl-paste"
    for cmd in ("xclip -selection clipboard -o", "xsel --clipboard --output"):
        if _command_exists(cmd.split()[0]):
            return cmd
    return None


def _command_exists(cmd: str) -> bool:
    """Check if a command exists on PATH."""
    return any(
        os.access(os.path.join(path, cmd), os.X_OK)
        for path in os.environ.get("PATH", "").split(os.pathsep)
        if os.path.isdir(path)
    )


def user_config_dir() -> str:
    """Return the user config directory."""
    pi = get_platform_info()
    if pi.os_name == "darwin":
        return os.path.join(os.environ.get("HOME", "~"), "Library", "Application Support", "keprix")
    if pi.os_name == "windows":
        return os.environ.get("APPDATA", os.path.join(os.environ.get("USERPROFILE", "~"), "AppData", "Roaming"))
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "keprix")
    return os.path.join(os.environ.get("HOME", "~"), ".config", "keprix")
