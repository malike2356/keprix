"""External $EDITOR compose helper for the Textual TUI (Prompt 206)."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path


def resolve_editor(explicit: str | None = None) -> str | None:
    editor = (explicit or os.environ.get("EDITOR") or os.environ.get("VISUAL") or "").strip()
    return editor or None


def edit_in_editor(initial: str, *, editor: str | None = None) -> str | None:
    """Open *initial* text in an external editor and return the edited content.

    Returns ``None`` when no editor is configured or the user aborts without saving.
    """
    command = resolve_editor(editor)
    if not command:
        return None

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as tmp:
        tmp.write(initial)
        tmp_path = tmp.name

    try:
        parts = shlex.split(command)
        if not parts:
            return None
        launch = [*parts, tmp_path]
        result = subprocess.run(launch, check=False)
        if result.returncode != 0:
            return None
        edited = Path(tmp_path).read_text(encoding="utf-8")
        return edited.rstrip("\n")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
