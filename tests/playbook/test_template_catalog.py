"""Studio template catalog tests."""

from __future__ import annotations

from keprix.playbook.canvas_compiler import compile_canvas_document
from keprix.playbook.canvas_decompiler import decompile_playbook_document
from keprix.playbook.template_catalog import get_template, list_templates
from keprix.playbook.yaml_compiler import compile_playbook_document


def test_template_gallery_lists_required_templates() -> None:
    templates = list_templates(include_custom=False)
    ids = {item["id"] for item in templates}

    assert len(templates) >= 5
    assert "aiva-deal-analyse" in ids
    assert "daily-digest" in ids
    assert "support-triage" in ids


def test_template_roundtrip_compiles() -> None:
    template = get_template("aiva-deal-analyse")
    assert template is not None

    canvas = decompile_playbook_document(template["yaml"])
    yaml_doc = compile_canvas_document(canvas)

    assert yaml_doc["variables"][0]["name"] == "property_url"
    assert compile_playbook_document(yaml_doc).graph_id == "aiva_deal_analyse"
