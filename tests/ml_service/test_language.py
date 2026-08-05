"""Prompt 231 language intelligence tests."""

from __future__ import annotations

import base64
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


class FakeSTT:
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        return audio_bytes.decode("utf-8")


class FakeTTS:
    async def synthesize(self, text: str, voice_id: str) -> bytes:
        return f"mp3:{voice_id}:{text}".encode("utf-8")


class FakeTranslator:
    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        return f"{text} [{src_lang}->{tgt_lang}]"


def _language_service():
    sys.path.insert(0, str(ML_SERVICE))
    try:
        module = _load_module("ml_service_language_service_test", ML_SERVICE / "services/language_service.py")
        return module.LanguageService(stt=FakeSTT(), tts=FakeTTS(), translator=FakeTranslator())
    finally:
        sys.path.remove(str(ML_SERVICE))


def test_detect_language_twi_heuristic() -> None:
    service = _language_service()
    result = service.detect_language("Mepa wo kyew")
    assert result["language"] == "tw"
    assert result["confidence"] >= 0.8


def test_translate_auto_detects_and_caches_shape() -> None:
    import asyncio

    service = _language_service()
    result = asyncio.run(service.translate("Mepa wo kyew", "auto", "en"))
    assert result == {"translated_text": "Mepa wo kyew [tw->en]", "src_lang": "tw"}


def test_transcribe_and_synthesize() -> None:
    import asyncio

    service = _language_service()
    audio = base64.b64encode(b"hello from audio").decode("ascii")
    transcript = asyncio.run(service.transcribe(audio, "audio/ogg", "auto"))
    assert transcript["text"] == "hello from audio"
    assert transcript["detected_language"] == "en"

    speech = asyncio.run(service.synthesize("reply", "voice-1"))
    assert speech["mime_type"] == "audio/mpeg"
    assert base64.b64decode(speech["audio_b64"]).startswith(b"mp3:voice-1")


def test_language_router_uses_service_dependency() -> None:
    sys.path.insert(0, str(ML_SERVICE))
    try:
        main = _load_module("ml_service_main_language_test", ML_SERVICE / "main.py")
        dependencies = sys.modules["dependencies"]
        dependencies.set_language_service(_language_service())
        client = TestClient(main.app)
        response = client.post("/language/detect", json={"text": "Mepa wo kyew"})
    finally:
        sys.path.remove(str(ML_SERVICE))

    assert response.status_code == 200
    assert response.json()["language"] == "tw"


def test_language_tool_handlers_format_json(monkeypatch) -> None:
    from keprix.tools import ml_service_tools

    def fake_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"path": path, **payload}

    monkeypatch.setattr(ml_service_tools, "_post_json", fake_post)
    detected = json.loads(ml_service_tools.detect_language_handler({"text": "Mepa wo kyew"}))
    translated = json.loads(ml_service_tools.translate_handler({"text": "Hello", "tgt_lang": "tw"}))
    transcribed = json.loads(ml_service_tools.transcribe_audio_handler({"audio_b64": "abc", "mime_type": "audio/ogg"}))
    speech = json.loads(ml_service_tools.synthesize_speech_handler({"text": "Hello"}))

    assert detected["path"] == "/language/detect"
    assert translated["src_lang"] == "auto"
    assert transcribed["language"] == "auto"
    assert speech["path"] == "/language/synthesize"


def test_nllb_server_and_compose_files_exist() -> None:
    assert (ML_SERVICE / "nllb_server/server.py").is_file()
    assert (ROOT / "docker-compose.ml.yml").is_file()
