"""Every .env.example variable appears in the generated env reference."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"
ENV_DOC = ROOT / "docs" / "configuration" / "environment-variables.md"


def _env_var_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            names.add(stripped.split("=", 1)[0].strip())
    return names


def test_env_reference_lists_all_example_variables() -> None:
    assert ENV_DOC.exists(), "Run scripts/generate-docs.sh first"
    expected = _env_var_names(ENV_EXAMPLE)
    doc = ENV_DOC.read_text(encoding="utf-8")
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]*)`", doc))
    missing = sorted(expected - documented)
    assert not missing, f"Missing from environment-variables.md: {missing}"
