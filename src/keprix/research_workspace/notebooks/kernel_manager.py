"""Runtime detection for Python and R."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from dataclasses import dataclass


PYTHON_SETUP = (
    "Python 3 is required. Verify with: python3 --version\n"
    "Optional packages: pandas, polars, duckdb, matplotlib, seaborn, scikit-learn, statsmodels"
)

R_SETUP = (
    "R is required for R script runs. Verify with: R --version\n"
    "Optional packages: tidyverse, jmv, survey (install with install.packages after approval)"
)


@dataclass
class RuntimeDetection:
    installed: bool
    binary: str | None
    version: str | None
    setup_instructions: str
    optional_packages: list[str]


def _optional_python_packages() -> list[str]:
    names = ["pandas", "polars", "duckdb", "matplotlib", "seaborn", "sklearn", "statsmodels"]
    available: list[str] = []
    for name in names:
        if importlib.util.find_spec(name) is not None:
            available.append(name)
    return available


def detect_python() -> RuntimeDetection:
    binary = shutil.which("python3") or shutil.which("python")
    if not binary:
        return RuntimeDetection(False, None, None, PYTHON_SETUP, [])
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version = (completed.stdout or completed.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        version = None
    return RuntimeDetection(True, binary, version, PYTHON_SETUP, _optional_python_packages())


def detect_r() -> RuntimeDetection:
    binary = shutil.which("Rscript") or shutil.which("R")
    if not binary:
        return RuntimeDetection(False, None, None, R_SETUP, [])
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version = (completed.stdout or completed.stderr or "").strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        version = None
    packages: list[str] = []
    try:
        probe = subprocess.run(
            [binary, "-e", 'cat(paste(rownames(installed.packages()), collapse=","))'],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        installed = set((probe.stdout or "").split(","))
        for name in ("tidyverse", "jmv", "survey"):
            if name in installed:
                packages.append(name)
    except (OSError, subprocess.TimeoutExpired):
        packages = []
    return RuntimeDetection(True, binary, version, R_SETUP, packages)
