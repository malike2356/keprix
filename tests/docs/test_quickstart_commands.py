"""Quickstart shell blocks are syntactically valid."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUICKSTART = ROOT / "docs" / "getting-started" / "quickstart.md"


def _bash_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    in_block = False
    lang = ""
    current: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("```"):
            if not in_block:
                in_block = True
                lang = line[3:].strip()
                current = []
            else:
                in_block = False
                if lang in {"", "bash", "sh", "shell"}:
                    blocks.append("\n".join(current))
            continue
        if in_block:
            current.append(line)
    return blocks


def test_quickstart_commands_parse() -> None:
    text = QUICKSTART.read_text(encoding="utf-8")
    blocks = _bash_blocks(text)
    assert blocks, "quickstart.md must include a bash code block"
    for block in blocks:
        script = f"set -euo pipefail\n{block}\n"
        proc = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
        assert proc.returncode == 0, proc.stderr


def test_quickstart_has_at_most_five_commands() -> None:
    text = QUICKSTART.read_text(encoding="utf-8")
    main_block = _bash_blocks(text)[0]
    commands = [line for line in main_block.splitlines() if line.strip() and not line.strip().startswith("#")]
    assert len(commands) <= 5, f"Expected at most 5 commands, found {len(commands)}"
