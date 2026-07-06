"""PSPP output parser tests."""

from __future__ import annotations

from pathlib import Path

from keprix.research_workspace.stats.pspp.output_parser import parse_output_file, parse_text_tables


def test_parse_text_tables():
    text = "Frequencies\nage  count\n30  1\n25  1\n\nDescriptives\nscore  mean\n70  70.0\n"
    tables = parse_text_tables(text)
    assert len(tables) >= 1
    assert tables[0]["title"] == "Frequencies"
    assert ["30", "1"] in tables[0]["rows"]


def test_parse_html_tables(tmp_path):
    html = """
    <html><body>
    <table>
      <tr><th>age</th><th>count</th></tr>
      <tr><td>30</td><td>1</td></tr>
    </table>
    </body></html>
    """
    path = tmp_path / "output.html"
    path.write_text(html, encoding="utf-8")
    parsed = parse_output_file(path)
    assert parsed["format"] == "html"
    assert parsed["tables"]
    assert parsed["tables"][0][1] == ["30", "1"]
