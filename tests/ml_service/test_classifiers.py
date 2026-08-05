"""Prompt 232 classifier tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
ML_SERVICE = ROOT / "apps/ml-service"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _classifier_service():
    sys.path.insert(0, str(ML_SERVICE))
    try:
        module = _load_module("ml_service_classifier_service_test", ML_SERVICE / "services/classifier_service.py")
        return module.ClassifierService()
    finally:
        sys.path.remove(str(ML_SERVICE))


def test_rule_classifiers_return_expected_outputs() -> None:
    service = _classifier_service()

    assert service.classify_intent("How much will it cost to drill at Tema?")["intent"] == "quote_request"
    assert service.classify_formation("fresh granite basement with fracture")["formation"] == "fresh_basement"
    assert service.predict_yield("fresh_basement", 80)["yield_class"] == "domestic"


def test_duplicate_member_detector_scores_candidates() -> None:
    service = _classifier_service()
    result = service.check_duplicate(
        "Kofi",
        "Mensah",
        phone="0241234567",
        dob="1980-01-01",
        existing_members=[
            {
                "member_number": "GBDA-001",
                "first_name": "Kofi",
                "last_name": "Mensah",
                "phone": "0241234567",
                "dob": "1980-01-01",
            }
        ],
    )

    assert result["is_likely_duplicate"] is True
    assert result["candidates"][0]["member_id"] == "GBDA-001"


def test_anomaly_detector_scores_unseen_transitions() -> None:
    service = _classifier_service()
    service.load_playbook("agent-1", [["lookup_member", "update_dues", "send_receipt"]])

    normal = service.detect_anomaly("agent-1", ["lookup_member", "update_dues", "send_receipt"])
    unusual = service.detect_anomaly("agent-1", ["delete_member", "wire_money"])

    assert normal["is_anomalous"] is False
    assert unusual["is_anomalous"] is True


def test_classifier_router_uses_service_dependency() -> None:
    sys.path.insert(0, str(ML_SERVICE))
    try:
        main = _load_module("ml_service_main_classifier_test", ML_SERVICE / "main.py")
        dependencies = sys.modules["dependencies"]
        dependencies.set_classifier_service(_classifier_service())
        client = TestClient(main.app)
        response = client.post("/classifiers/intent", json={"text": "when are my dues due"})
    finally:
        sys.path.remove(str(ML_SERVICE))

    assert response.status_code == 200
    assert response.json()["intent"] == "dues_inquiry"


def test_classifier_tool_handlers_format_json(monkeypatch) -> None:
    from keprix.tools import ml_service_tools

    def fake_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"path": path, **payload}

    monkeypatch.setattr(ml_service_tools, "_post_json", fake_post)

    assert json.loads(ml_service_tools.classify_intent_handler({"text": "hello"}))["path"] == "/classifiers/intent"
    assert json.loads(ml_service_tools.classify_formation_handler({"description": "sandstone"}))["path"] == "/classifiers/formation"
    assert json.loads(ml_service_tools.predict_yield_handler({"formation": "sandstone", "depth_m": 50}))["path"] == "/classifiers/yield"
    assert json.loads(ml_service_tools.check_duplicate_member_handler({"first_name": "A", "last_name": "B"}))["path"] == "/classifiers/duplicate"
    assert json.loads(ml_service_tools.detect_agent_anomaly_handler({"agent_id": "a", "action_sequence": []}))["path"] == "/classifiers/anomaly"


def test_training_artifacts_exist() -> None:
    assert (ROOT / "database/migrations/0006_training_log.sql").is_file()
    assert (ML_SERVICE / "train/train_intent.py").is_file()
    assert (ML_SERVICE / "train/train_formation.py").is_file()
    assert (ML_SERVICE / "train/train_yield.py").is_file()
