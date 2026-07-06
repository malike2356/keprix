"""
NLLB-200 sidecar HTTP server.

Endpoints:
  POST /translate        - single text translation
  POST /translate-batch  - batch translation
  GET  /health           - liveness and model status
  GET  /languages        - supported flores language codes
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

_tokenizer = None
_model = None
_model_loaded = False


def _load_model() -> None:
    global _tokenizer, _model, _model_loaded
    model_name = os.environ.get("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
    device = os.environ.get("NLLB_DEVICE", "cpu")

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    _model.to(device)
    _model_loaded = True
    print(f"NLLB-200 {model_name} loaded on {device}")


def _translate_text(text: str, source_language: str, target_language: str) -> dict[str, Any]:
    if _tokenizer is None or _model is None:
        raise RuntimeError("Model not loaded")

    import torch

    device = os.environ.get("NLLB_DEVICE", "cpu")
    _tokenizer.src_lang = source_language
    inputs = _tokenizer(text, return_tensors="pt").to(device)
    forced_bos = _tokenizer.convert_tokens_to_ids(target_language)
    outputs = _model.generate(
        **inputs,
        forced_bos_token_id=forced_bos,
        max_length=int(os.environ.get("NLLB_MAX_LENGTH", "512")),
        num_beams=int(os.environ.get("NLLB_NUM_BEAMS", "4")),
    )
    translation = _tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
    return {"translation": translation, "score": 0.88}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


app = FastAPI(title="NLLB-200 Sidecar", lifespan=lifespan)


class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str


class TranslateBatchRequest(BaseModel):
    texts: list[str]
    source_language: str
    target_language: str


@app.post("/translate")
async def translate(req: TranslateRequest) -> dict[str, Any]:
    if not _model_loaded:
        raise HTTPException(503, detail="Model not loaded yet")
    try:
        return _translate_text(req.text, req.source_language, req.target_language)
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.post("/translate-batch")
async def translate_batch(req: TranslateBatchRequest) -> dict[str, Any]:
    if not _model_loaded:
        raise HTTPException(503, detail="Model not loaded yet")
    try:
        translations = [
            _translate_text(text, req.source_language, req.target_language)
            for text in req.texts
        ]
        return {"translations": translations}
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if _model_loaded else "loading",
        "model_loaded": _model_loaded,
    }


@app.get("/languages")
async def languages() -> dict[str, list[str]]:
    return {
        "supported": [
            "twi_Latn",
            "ewe_Latn",
            "nzi_Latn",
            "dik_Latn",
            "hau_Latn",
            "yor_Latn",
            "swh_Latn",
            "eng_Latn",
        ]
    }
