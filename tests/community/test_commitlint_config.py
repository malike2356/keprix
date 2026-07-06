"""Commitlint configuration for Conventional Commits enforcement."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "commitlint.config.js"
PACKAGE = ROOT / "package.json"


def test_commitlint_config_exists() -> None:
    assert CONFIG.is_file(), "commitlint.config.js must exist at repo root"


def test_root_package_json_declares_commitlint() -> None:
    data = json.loads(PACKAGE.read_text(encoding="utf-8"))
    deps = data.get("devDependencies", {})
    assert "@commitlint/cli" in deps
    assert "@commitlint/config-conventional" in deps
    assert "commitlint" in data.get("scripts", {})


def test_commitlint_config_lists_core_types() -> None:
    text = CONFIG.read_text(encoding="utf-8")
    assert '"feat"' in text
    assert '"fix"' in text
    assert '"chore"' in text


@pytest.mark.skipif(shutil.which("pnpm") is None, reason="pnpm not installed")
def test_commitlint_cli_rejects_invalid_message() -> None:
    if not (ROOT / "node_modules").is_dir():
        pytest.skip("root node_modules not installed; run pnpm install at repo root")

    bad = subprocess.run(
        ["pnpm", "exec", "commitlint"],
        cwd=ROOT,
        input="bad commit message\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode != 0, bad.stdout + bad.stderr


@pytest.mark.skipif(shutil.which("pnpm") is None, reason="pnpm not installed")
def test_commitlint_cli_accepts_conventional_message() -> None:
    if not (ROOT / "node_modules").is_dir():
        pytest.skip("root node_modules not installed; run pnpm install at repo root")

    good = subprocess.run(
        ["pnpm", "exec", "commitlint"],
        cwd=ROOT,
        input="feat(frontend): add changelog hero\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert good.returncode == 0, good.stdout + good.stderr
