from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_language_service
from services.language_service import LanguageService
from utils.errors import UnsupportedLanguageError

router = APIRouter()


class DetectRequest(BaseModel):
    text: str


class TranslateRequest(BaseModel):
    text: str
    src_lang: str = "auto"
    tgt_lang: str


class TranscribeRequest(BaseModel):
    audio_b64: str
    mime_type: str
    language: str = "auto"


class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    voice_id: str = ""


@router.post("/detect")
async def detect_language(req: DetectRequest, svc: LanguageService = Depends(get_language_service)) -> dict:
    return svc.detect_language(req.text)


@router.post("/translate")
async def translate(req: TranslateRequest, svc: LanguageService = Depends(get_language_service)) -> dict:
    return await svc.translate(req.text, req.src_lang, req.tgt_lang)


@router.post("/transcribe")
async def transcribe(req: TranscribeRequest, svc: LanguageService = Depends(get_language_service)) -> dict:
    try:
        return await svc.transcribe(req.audio_b64, req.mime_type, req.language)
    except UnsupportedLanguageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest, svc: LanguageService = Depends(get_language_service)) -> dict:
    return await svc.synthesize(req.text, req.voice_id)
