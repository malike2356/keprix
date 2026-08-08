from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-release.sh"


def run(*args: str, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PYTHON"] = sys.executable
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_release_installer_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_exact_version_dry_run_is_immutable(tmp_path: Path) -> None:
    result = run("--version", "0.16.0", "--dry-run", home=tmp_path)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "/releases/download/v0.16.0/release-manifest.json" in output
    assert "/main/" not in output
    assert not (tmp_path / ".local/share/keprix").exists()


def test_uninstall_dry_run_preserves_data_by_default(tmp_path: Path) -> None:
    result = run("--uninstall", "--dry-run", home=tmp_path)
    assert result.returncode == 0
    assert "will be preserved" in result.stdout


def test_refuses_broad_prefix(tmp_path: Path) -> None:
    result = run("--prefix", str(tmp_path), "--version", "0.16.0", "--dry-run", home=tmp_path)
    assert result.returncode != 0
    assert "broad installation prefix" in result.stderr
