"""Prompt 268 external notebook bridge tests."""

from __future__ import annotations

import json

from keprix.research.notebook_bridge import NotebookExternalBridge, NotebookResearchConfig
from keprix.research.notebook_native import normalize_notebook_source


class Completed:
    returncode = 0
    stderr = ""
    stdout = json.dumps(
        {
            "external_notebook_id": "notebook-1",
            "report_md": "# External\n\nResult [S1]",
            "citations": [{"id": "S1", "title": "Source"}],
        }
    )


def test_external_bridge_spawns_configured_command(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_run(command, input, capture_output, text, timeout, check):
        calls.append(
            {
                "command": command,
                "input": json.loads(input),
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
                "check": check,
            }
        )
        return Completed()

    monkeypatch.setattr("keprix.research.notebook_bridge.subprocess.run", fake_run)
    bridge = NotebookExternalBridge(
        config=NotebookResearchConfig(
            enabled=True,
            external_enabled=True,
            external_command="/usr/bin/notebooklm --json",
        ),
        timeout=7,
    )
    sources = [normalize_notebook_source({"kind": "text", "ref": "Alpha"}), normalize_notebook_source({"kind": "text", "ref": "Beta"})]

    result = bridge.run(query="alpha", sources=sources)

    assert result["external_notebook_id"] == "notebook-1"
    assert calls[0]["command"] == ["/usr/bin/notebooklm", "--json"]
    assert calls[0]["input"]["tools"] == ["notebook_create", "notebook_add_source", "notebook_query", "notebook_export"]
    assert calls[0]["timeout"] == 7
