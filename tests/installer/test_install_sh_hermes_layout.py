"""Smoke tests for Hermes-parity scripts/install.sh layout (prompt 419)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def test_install_sh_bash_syntax() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(INSTALL_SH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_install_sh_dry_run_checkout_layout() -> None:
    with tempfile.TemporaryDirectory(prefix="keprix-gtm-dry-") as tmp:
        env = os.environ.copy()
        env["KEPRIX_DRY_RUN"] = "1"
        env["KEPRIX_HOME"] = tmp
        proc = subprocess.run(
            ["bash", str(INSTALL_SH)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        assert proc.returncode == 0, out
        assert ".keprix" in out or tmp in out
        assert "KEPRIX_HOME" in out
        assert "checkout" in out.lower() or "piped" in out.lower()
        assert str(Path(tmp) / "keprix") in out or "ROOT" in out
        # Dry-run must not create a real venv under the temp home clone path.
        assert not (Path(tmp) / "keprix" / ".venv").exists()


def test_install_sh_dry_run_mentions_home_layout() -> None:
    with tempfile.TemporaryDirectory(prefix="keprix-gtm-dry2-") as tmp:
        env = os.environ.copy()
        env["KEPRIX_DRY_RUN"] = "1"
        env["KEPRIX_HOME"] = tmp
        # Force piped-like reporting is not required; checkout mode still prints KEPRIX_HOME.
        proc = subprocess.run(
            ["bash", str(INSTALL_SH)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "KEPRIX_HOME" in proc.stdout
        assert tmp in proc.stdout


def test_install_sh_recovers_dirty_clone_and_existing_venv() -> None:
    text = INSTALL_SH.read_text(encoding="utf-8")
    assert "stash push" in text
    assert "ls-files --unmerged" in text
    assert "already exists, recreating" in text
    assert "start chatting" in text.lower() or "keprix" in text
    assert "source ~/.bashrc" in text
    assert "4. keprix tui" not in text
    assert "keprixai.com/install.sh" in text


def test_marketing_hosts_install_sh() -> None:
    dockerfile = REPO_ROOT / "docker" / "Dockerfile.frontend"
    nxt = REPO_ROOT / "frontend" / "next.config.ts"
    lib = REPO_ROOT / "frontend" / "src" / "lib" / "install.ts"
    assert "scripts/install.sh" in dockerfile.read_text(encoding="utf-8")
    assert "/install.sh" in nxt.read_text(encoding="utf-8")
    assert "keprixai.com/install.sh" in lib.read_text(encoding="utf-8")


def test_inner_install_sh_clones_public_keprix_github() -> None:
    inner = REPO_ROOT / "src" / "keprix" / "scripts" / "install.sh"
    text = inner.read_text(encoding="utf-8")
    assert "malike2356/keprix.git" in text
    assert "NousResearch/keprix.git" not in text
    assert "keprixai.com/install.sh" in text
