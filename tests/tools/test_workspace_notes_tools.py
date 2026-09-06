import json

from keprix.tools import workspace_notes_tools as notes


def test_workspace_notes_crud_is_workspace_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(notes.Path, "home", staticmethod(lambda: tmp_path))
    created = json.loads(notes.workspace_notes_create({"workspace_id": "ws-a", "title": "Plan", "body": "Ship it"}))
    assert json.loads(notes.workspace_notes_list({"workspace_id": "ws-b"})) == []
    updated = json.loads(notes.workspace_notes_update({"workspace_id": "ws-a", "note_id": created["id"], "body": "Ship it today"}))
    assert updated["body"] == "Ship it today"
    assert json.loads(notes.workspace_notes_delete({"workspace_id": "ws-a", "note_id": created["id"]}))["ok"] is True
    assert json.loads(notes.workspace_notes_list({"workspace_id": "ws-a"})) == []


def test_workspace_notes_reject_empty_content(tmp_path, monkeypatch):
    monkeypatch.setattr(notes.Path, "home", staticmethod(lambda: tmp_path))
    result = json.loads(notes.workspace_notes_create({"title": "", "body": ""}))
    assert result["status"] == "invalid"
