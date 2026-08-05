"""External link opening helpers."""

from __future__ import annotations

import subprocess

from keprix.tui.platform_detect import get_platform_info


def open_external_link(url: str) -> subprocess.Popen[str]:
    platform = get_platform_info()
    if platform.os_name == "darwin":
        command = ["open", url]
    elif platform.os_name == "windows":
        command = ["cmd", "/c", "start", "", url]
    else:
        command = ["xdg-open", url]
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

