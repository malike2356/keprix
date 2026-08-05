"""Prompt 229 ML service scaffold tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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


def test_ml_service_health_endpoint() -> None:
    sys.path.insert(0, str(ML_SERVICE))
    try:
        main = _load_module("ml_service_main_test", ML_SERVICE / "main.py")
        client = TestClient(main.app)
        response = client.get("/health")
    finally:
        sys.path.remove(str(ML_SERVICE))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chunk_document_fallback() -> None:
    sys.path.insert(0, str(ML_SERVICE))
    try:
        chunking = _load_module("ml_service_chunking_test", ML_SERVICE / "utils/chunking.py")
        chunks = chunking.chunk_document("one two three four five", max_tokens=2, overlap_tokens=1)
    finally:
        sys.path.remove(str(ML_SERVICE))

    assert [chunk.text for chunk in chunks] == ["one two", "two three", "three four", "four five"]


def test_ml_tools_registered_as_not_ready() -> None:
    import keprix.tools.ml_service_tools  # noqa: F401
    from keprix.tools.registry import registry

    implemented = {
        "search_domain_knowledge",
        "detect_language",
        "translate",
        "transcribe_audio",
        "synthesize_speech",
        "classify_intent",
        "classify_formation",
        "predict_yield",
        "check_duplicate_member",
        "detect_agent_anomaly",
    }
    for name in [
        "detect_language",
        "translate",
        "transcribe_audio",
        "synthesize_speech",
        "classify_intent",
        "classify_formation",
        "predict_yield",
        "check_duplicate_member",
        "detect_agent_anomaly",
    ]:
        entry = registry.get_entry(name)
        assert entry is not None
        assert entry.toolset == "ml-service"
        result = json.loads(registry.dispatch(name, {}))
        if name not in implemented:
            assert result["status"] == "not_ready"


def test_ml_client_package_files_exist() -> None:
    assert (ROOT / "packages/ml-client/src/index.ts").is_file()
    assert (ROOT / "packages/ml-client/src/embedding-client.ts").is_file()
    assert (ROOT / "packages/ml-client/src/language-client.ts").is_file()
    assert (ROOT / "packages/ml-client/src/classifier-client.ts").is_file()
