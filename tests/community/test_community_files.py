"""Community infrastructure validation."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_validate_community_files_script_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", "scripts/validate-community-files.sh"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
