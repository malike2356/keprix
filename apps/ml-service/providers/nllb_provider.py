import httpx

from providers.base import TranslationProvider

NLLB_LANG_MAP: dict[str, str] = {
    "en": "eng_Latn",
    "tw": "twi_Latn",
    "ee": "ewe_Latn",
    "gaa": "gaa_Latn",
    "ha": "hau_Latn",
    "dag": "daa_Latn",
    "fr": "fra_Latn",
    "pt": "por_Latn",
    "ar": "arb_Arab",
}


class NLLBProvider(TranslationProvider):
    def __init__(self, service_url: str = "http://nllb-service:8210"):
        self.url = service_url.rstrip("/")

    def _to_nllb(self, lang: str) -> str:
        code = NLLB_LANG_MAP.get(lang)
        if not code:
            raise ValueError(f"Unsupported language for NLLB: {lang}")
        return code

    async def translate(self, text: str, src_lang: str, tgt_lang: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.url}/translate",
                json={
                    "text": text,
                    "src_lang": self._to_nllb(src_lang),
                    "tgt_lang": self._to_nllb(tgt_lang),
                },
            )
            response.raise_for_status()
            return response.json()["translated_text"]
