import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
MODEL_PATH = os.environ.get("MODEL_PATH", "facebook/nllb-200-distilled-600M")
_pipeline = None


class TranslateRequest(BaseModel):
    text: str
    src_lang: str
    tgt_lang: str
    max_new_tokens: int = 400


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
        _pipeline = pipeline("translation", model=model, tokenizer=tokenizer)
    return _pipeline


@app.post("/translate")
def translate(req: TranslateRequest):
    pipe = get_pipeline()
    result = pipe(req.text, src_lang=req.src_lang, tgt_lang=req.tgt_lang, max_length=req.max_new_tokens)
    return {"translated_text": result[0]["translation_text"]}


@app.get("/health")
def health():
    return {"status": "ok"}
