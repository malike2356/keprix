"""Known DAP adapter commands and conservative availability checks."""

from __future__ import annotations

import shutil
import sys
from typing import Any


def adapter_command(language: str) -> list[str]:
    language = language.lower().replace("c++", "c_cpp")
    if language == "python":
        return [sys.executable, "-m", "debugpy.adapter"]
    if language in {"rust", "c_cpp"}:
        return ["lldb-dap"]
    if language == "go":
        return ["dlv", "dap", "--listen=127.0.0.1:0"]
    raise ValueError(f"unsupported debug language: {language}")


def adapter_available(language: str) -> bool:
    try:
        command = adapter_command(language)
    except ValueError:
        return False
    if command[0] == sys.executable:
        try:
            import debugpy  # noqa: F401
        except ImportError:
            return False
        return True
    return shutil.which(command[0]) is not None


def adapter_status() -> dict[str, dict[str, Any]]:
    return {
        language: {"available": adapter_available(language), "command": adapter_command(language)}
        for language in ("python", "rust", "c_cpp", "go")
    }
