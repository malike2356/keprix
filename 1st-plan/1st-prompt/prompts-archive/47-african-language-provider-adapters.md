# keprix - Prompt 47: African Language Provider Adapters

## Context

Read `35-localization-language-voice.md` thoroughly before starting. This prompt implements two specific provider adapters that extend Prompt 27's provider routing layer. Prompt 27 specified a provider abstraction with `base.py`, `local.py`, `cloud.py`, `whisper.py`, and placeholders for cloud providers. This prompt adds `seamless_m4t.py` and `nllb_200.py`, updates the provider router to prefer these for African languages, and supplies Docker configuration for self-hosted deployment of both models.

Do not re-implement anything from Prompt 27. Only add what is specified here.

---

## Why These Two Models

**SeamlessM4T v2** is Meta's unified multilingual speech model. It handles four tasks in one model: speech-to-text (S2T), text-to-text (T2T), text-to-speech (T2S), and speech-to-speech (S2S). For Ghanaian and West African languages this is the best available open-weight option because it was trained on more African speech data than Whisper, handles Twi/Akan, Ewe, Ga, Fante, Dagbani, Hausa, and Yoruba at reasonable quality, and produces confidence scores useful for the localization audit.

**NLLB-200** (No Language Left Behind) is Meta's translation-only model covering 200 languages including many that SeamlessM4T misses. It is text-to-text only (no speech). Use it as the fallback for translation tasks when SM4T does not support the target language pair, and as a standalone option when speech is not needed.

The combination covers over 95% of the African language pairs AbbiS, COMPASS, and future products will need.

---

## File Structure

```
keprix/backend/localization/providers/
    seamless_m4t.py         - SeamlessM4T v2 provider adapter
    nllb_200.py             - NLLB-200 provider adapter
    language_matrix.py      - cross-provider language support matrix

keprix/backend/localization/
    router.py               - UPDATED: extend existing router with SM4T and NLLB priority rules

keprix/docker/
    seamless-m4t/
        Dockerfile
        entrypoint.sh
        requirements.txt
    nllb-200/
        Dockerfile
        entrypoint.sh
        requirements.txt

docker-compose.localization.yml  - optional compose file to run both model services

keprix/tests/localization/
    test_seamless_m4t.py
    test_nllb_200.py
    test_language_matrix.py
```

---

## Language Code Mapping

SeamlessM4T and NLLB use different internal language codes. Both differ from BCP 47. The localization module uses BCP 47 throughout its public API. Adapter code translates between them.

### SeamlessM4T Language Codes (partial - African languages)

| BCP 47 | SM4T code | Language |
|--------|-----------|----------|
| `ak-GH` / `tw-GH` | `twi` | Twi / Akan |
| `ee-GH` | `ewe` | Ewe |
| `gaa-GH` | `gaa` | Ga |
| `ha-NG` / `ha-GH` | `hau` | Hausa |
| `yo-NG` | `yor` | Yoruba |
| `ig-NG` | `ibo` | Igbo |
| `dag-GH` | `dik` | Dagbani |
| `sw-KE` / `sw-TZ` | `swh` | Swahili |
| `am-ET` | `amh` | Amharic |
| `so-SO` | `som` | Somali |
| `zu-ZA` | `zul` | Zulu |
| `pcm-NG` | `pcm` | Nigerian Pidgin |
| `en-GH` | `eng` | English (Ghana) |
| `fr-SN` | `fra` | French (West Africa) |

### NLLB Language Codes (partial - African languages)

| BCP 47 | NLLB flores code | Language |
|--------|-----------------|----------|
| `ak-GH` / `tw-GH` | `twi_Latn` | Twi / Akan |
| `ee-GH` | `ewe_Latn` | Ewe |
| `gaa-GH` | `gaa_Latn` | Ga |
| `fan-GH` | `aka_Latn` | Fante (Akan family) |
| `nzi-GH` | `nzi_Latn` | Nzema |
| `dag-GH` | `dik_Latn` | Dagbani |
| `ha-NG` | `hau_Latn` | Hausa (Latin script) |
| `yo-NG` | `yor_Latn` | Yoruba |
| `ig-NG` | `ibo_Latn` | Igbo |
| `sw-KE` | `swh_Latn` | Swahili |
| `am-ET` | `amh_Ethi` | Amharic |
| `ar-EG` | `arz_Arab` | Egyptian Arabic |
| `ary-MA` | `ary_Arab` | Moroccan Darija |

Build `language_matrix.py` with the complete mapping tables and a helper function:

```python
def bcp47_to_sm4t(code: str) -> str | None:
    """Returns SM4T internal code for BCP 47 code, or None if not supported."""

def bcp47_to_nllb(code: str) -> str | None:
    """Returns NLLB flores code for BCP 47 code, or None if not supported."""

def sm4t_supports(source: str, target: str, task: str) -> bool:
    """Returns True if SM4T supports this (source, target, task) triple.
    task: 's2t', 't2t', 't2s', 's2s'
    """

def nllb_supports(source: str, target: str) -> bool:
    """Returns True if NLLB supports this translation pair."""
```

---

## SeamlessM4T Provider Adapter

### Deployment Options

**Option A: Direct Python library (self-hosted, same process)**

```python
# In seamless_m4t.py
from seamless_communication.models.inference import Translator, VocoderType
```

Requires `seamless_communication` package (~5GB model download on first use). The model is loaded once at startup and cached in memory. Suitable for a keprix instance with GPU or a high-RAM CPU server.

**Option B: Sidecar HTTP service (Docker)**

keprix calls a local HTTP endpoint served by a separate Docker container running the SM4T model. The sidecar exposes a REST API that mirrors the adapter interface. This is the recommended production deployment - it isolates the large model from the main keprix process, allows independent scaling, and lets keprix restart without reloading the model.

Implement both options. Select via config:

```yaml
localization:
  providers:
    seamless_m4t:
      mode: sidecar             # 'direct' or 'sidecar'
      sidecar_url: http://seamless-m4t:7810
      direct_model: seamlessM4T_v2_large
      device: cpu               # 'cpu' or 'cuda'
      dtype: fp16               # 'fp16' or 'fp32'
```

### Adapter Implementation

```python
# keprix/backend/localization/providers/seamless_m4t.py

from keprix.backend.localization.providers.base import LocalizationProvider
from keprix.backend.localization.schemas import (
    TranscriptionResult, TranslationResult, SpeechSynthesisResult,
    TranscriptSegment
)
from keprix.backend.localization.providers.language_matrix import (
    bcp47_to_sm4t, sm4t_supports
)

class SeamlessM4TProvider(LocalizationProvider):
    name = "seamless_m4t"
    capabilities = {"transcription", "translation", "speech"}

    async def transcribe(
        self,
        audio_bytes: bytes,
        source_language: str | None = None,
        target_language: str = "en",
    ) -> TranscriptionResult:
        """
        Speech-to-text: audio in source_language -> text in target_language.
        If source_language is None, SM4T performs language identification first.
        """
        sm4t_src = bcp47_to_sm4t(source_language) if source_language else None
        sm4t_tgt = bcp47_to_sm4t(target_language) or "eng"

        if sm4t_src and not sm4t_supports(sm4t_src, sm4t_tgt, "s2t"):
            raise LanguagePairUnsupported(source_language, target_language, "s2t", "seamless_m4t")

        payload = {
            "task": "s2t",
            "audio": audio_bytes_to_base64(audio_bytes),
            "source_language": sm4t_src,
            "target_language": sm4t_tgt,
        }
        result = await self._call(payload)

        return TranscriptionResult(
            language_code=sm4t_to_bcp47(result["detected_language"]),
            transcript=result["text"],
            confidence=result.get("confidence", 0.0),
            segments=[
                TranscriptSegment(
                    start=s["start"], end=s["end"], text=s["text"], confidence=s.get("confidence")
                )
                for s in result.get("segments", [])
            ],
            provider="seamless_m4t",
        )

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        """
        Text-to-text translation with optional term preservation.
        """
        sm4t_src = bcp47_to_sm4t(source_language)
        sm4t_tgt = bcp47_to_sm4t(target_language)

        if not sm4t_src or not sm4t_tgt:
            raise LanguagePairUnsupported(source_language, target_language, "t2t", "seamless_m4t")

        protected_text = protect_terms(text, preserve_terms or [])
        payload = {
            "task": "t2t",
            "text": protected_text,
            "source_language": sm4t_src,
            "target_language": sm4t_tgt,
        }
        result = await self._call(payload)
        translated = restore_terms(result["text"], preserve_terms or [])

        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=translated,
            confidence=result.get("confidence", 0.0),
            glossary_matches=[],
            warnings=[],
            provider="seamless_m4t",
        )

    async def synthesize_speech(
        self,
        text: str,
        language: str,
        voice_id: str | None = None,
    ) -> SpeechSynthesisResult:
        """
        Text-to-speech: returns audio bytes in the target language.
        """
        sm4t_lang = bcp47_to_sm4t(language)
        if not sm4t_lang or not sm4t_supports(sm4t_lang, sm4t_lang, "t2s"):
            raise LanguagePairUnsupported(language, language, "t2s", "seamless_m4t")

        payload = {"task": "t2s", "text": text, "target_language": sm4t_lang}
        result = await self._call(payload)
        audio_url = await store_audio(result["audio_base64"], language, "seamless_m4t")

        return SpeechSynthesisResult(
            language_code=language,
            voice_id="seamless_m4t_default",
            audio_url=audio_url,
            transcript=text,
            provider="seamless_m4t",
        )

    async def _call(self, payload: dict) -> dict:
        """Call sidecar or direct library based on config."""
        if self.config.mode == "sidecar":
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f"{self.config.sidecar_url}/infer", json=payload)
                r.raise_for_status()
                return r.json()
        else:
            return await self._call_direct(payload)

    async def health_check(self) -> dict:
        try:
            if self.config.mode == "sidecar":
                r = await httpx.AsyncClient(timeout=5).get(f"{self.config.sidecar_url}/health")
                return {"status": "ok" if r.status_code == 200 else "degraded"}
            else:
                return {"status": "ok", "mode": "direct"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
```

### Term Preservation

Both `protect_terms` and `restore_terms` use placeholder substitution: replace each preserved term with a unique token (e.g., `__TERM_0__`, `__TERM_1__`) before sending to the model, then restore after. This prevents the model from translating technical terms that must remain in English.

```python
def protect_terms(text: str, terms: list[str]) -> tuple[str, dict]:
    """Replace terms with placeholders. Returns modified text and restore map."""
    restore_map = {}
    for i, term in enumerate(sorted(terms, key=len, reverse=True)):
        placeholder = f"__TERM_{i}__"
        if term.lower() in text.lower():
            text = re.sub(re.escape(term), placeholder, text, flags=re.IGNORECASE)
            restore_map[placeholder] = term
    return text, restore_map

def restore_terms(text: str, restore_map: dict) -> str:
    for placeholder, term in restore_map.items():
        text = text.replace(placeholder, term)
    return text
```

---

## NLLB-200 Provider Adapter

NLLB-200 is text-to-text only. It does not support speech. Its role is:
1. Translation fallback when SM4T does not support the language pair.
2. Primary translator for languages where NLLB has better coverage than SM4T.
3. Batch translation for glossary and corpus preparation.

### Model Selection

Use `facebook/nllb-200-distilled-600M` by default (faster, lower RAM). Configure `facebook/nllb-200-1.3B` for higher accuracy when the server has sufficient memory.

```yaml
localization:
  providers:
    nllb_200:
      mode: sidecar
      sidecar_url: http://nllb-200:7811
      model: facebook/nllb-200-distilled-600M
      max_length: 512
      num_beams: 4
      device: cpu
```

### Adapter Implementation

```python
# keprix/backend/localization/providers/nllb_200.py

class NLLB200Provider(LocalizationProvider):
    name = "nllb_200"
    capabilities = {"translation"}   # no transcription, no speech

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_terms: list[str] | None = None,
    ) -> TranslationResult:
        nllb_src = bcp47_to_nllb(source_language)
        nllb_tgt = bcp47_to_nllb(target_language)

        if not nllb_src or not nllb_tgt:
            raise LanguagePairUnsupported(source_language, target_language, "t2t", "nllb_200")

        protected_text, restore_map = protect_terms(text, preserve_terms or [])
        payload = {
            "text": protected_text,
            "source_language": nllb_src,
            "target_language": nllb_tgt,
        }
        result = await self._call(payload)
        translated = restore_terms(result["translation"], restore_map)

        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            source_text=text,
            translated_text=translated,
            confidence=result.get("score", 0.0),   # NLLB returns sequence log-prob as score
            glossary_matches=[],
            warnings=[],
            provider="nllb_200",
        )

    async def batch_translate(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[TranslationResult]:
        """Translate multiple texts in one API call. More efficient than looping."""

    async def health_check(self) -> dict: ...
```

---

## Docker Sidecar Services

### SeamlessM4T Sidecar (`keprix/docker/seamless-m4t/`)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
RUN pip install seamless_communication torch --index-url https://download.pytorch.org/whl/cpu
WORKDIR /app
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 7810
CMD ["./entrypoint.sh"]
```

**entrypoint.sh:**
```bash
#!/bin/bash
# Download model on first run, then serve
python -c "
from seamless_communication.models.inference import Translator
print('Loading SeamlessM4T v2...')
translator = Translator('seamlessM4T_v2_large', vocoder_name_or_card='vocoder_v2', device='cpu', dtype='fp16')
print('Model loaded. Starting server...')
"
uvicorn server:app --host 0.0.0.0 --port 7810
```

The `server.py` in the sidecar exposes:
- `POST /infer` - `{task, audio?, text?, source_language, target_language}` -> `{text?, audio_base64?, confidence, detected_language?, segments?}`
- `GET /health` - `{status, model_loaded, supported_language_count}`
- `GET /languages` - list of supported language codes per task

### NLLB-200 Sidecar (`keprix/docker/nllb-200/`)

Similar pattern. Exposes:
- `POST /translate` - `{text, source_language, target_language}` -> `{translation, score}`
- `POST /translate-batch` - `{texts: [], source_language, target_language}` -> `{translations: []}`
- `GET /health`
- `GET /languages`

### docker-compose.localization.yml

```yaml
services:
  seamless-m4t:
    build: ./keprix/docker/seamless-m4t
    ports:
      - "7810:7810"
    volumes:
      - seamless_models:/root/.cache/huggingface
    environment:
      - MODEL=seamlessM4T_v2_large
      - DEVICE=cpu
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7810/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nllb-200:
    build: ./keprix/docker/nllb-200
    ports:
      - "7811:7811"
    volumes:
      - nllb_models:/root/.cache/huggingface
    environment:
      - MODEL=facebook/nllb-200-distilled-600M
      - DEVICE=cpu
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7811/health"]
      interval: 30s
      timeout: 10s

volumes:
  seamless_models:
  nllb_models:
```

---

## Provider Router Extension

Update `keprix/backend/localization/router.py` (created in Prompt 27) to add SM4T and NLLB priority:

```python
# Provider selection priority for African languages
AFRICAN_LANGUAGE_PREFIXES = {
    "ak", "tw", "ee", "gaa", "fan", "nzi", "dag", "ha", "yo", "ig",
    "pcm", "wo", "bm", "sw", "am", "om", "so", "rw", "zu", "xh",
    "st", "tn", "sn", "ny", "ln", "ar", "ary", "kab"
}

def select_transcription_provider(source_language: str, config: LocalizationConfig) -> str:
    lang_prefix = source_language.split("-")[0].lower()
    if lang_prefix in AFRICAN_LANGUAGE_PREFIXES and config.seamless_m4t.enabled:
        if sm4t_supports_s2t(source_language):
            return "seamless_m4t"
    if config.whisper.enabled:
        return "whisper"
    return "cloud"

def select_translation_provider(source: str, target: str, config: LocalizationConfig) -> str:
    src_prefix = source.split("-")[0].lower()
    if src_prefix in AFRICAN_LANGUAGE_PREFIXES or target.split("-")[0].lower() in AFRICAN_LANGUAGE_PREFIXES:
        if config.seamless_m4t.enabled and sm4t_supports_t2t(source, target):
            return "seamless_m4t"
        if config.nllb_200.enabled and nllb_supports(source, target):
            return "nllb_200"
    return "cloud"

def select_speech_provider(language: str, config: LocalizationConfig) -> str:
    lang_prefix = language.split("-")[0].lower()
    # Check voice templates first (Prompt 49)
    if voice_template_library.has_templates(language):
        return "voice_templates"
    if lang_prefix in AFRICAN_LANGUAGE_PREFIXES and config.seamless_m4t.enabled:
        if sm4t_supports_t2s(language):
            return "seamless_m4t"
    return "cloud"
```

---

## 2025 Ghanaian ASR Dataset Integration

A 2025 research dataset provides 5,000 hours of speech data for Akan, Ewe, Dagbani, Dagaare, and Ikposo. This dataset is used for fine-tuning SeamlessM4T to improve accuracy on borehole domain speech.

Document the dataset reference in `keprix/docker/seamless-m4t/FINE_TUNING.md`:
- Dataset DOI and access URL (sciencedirect.com 2025 publication).
- Format: audio files + transcripts.
- Languages covered.
- How to convert to SM4T fine-tuning format.
- Expected accuracy improvement on Ghanaian speech after fine-tuning.

Fine-tuning itself is a separate ML task run outside of keprix's normal build. The sidecar architecture makes it simple to swap in a fine-tuned model: replace the model path in the environment variable without modifying any keprix code.

Mozilla Common Voice Twi data (community-contributed recordings) supplements the dataset. Include instructions for downloading it in `FINE_TUNING.md`.

---

## Acceptance Criteria

- `SeamlessM4TProvider.transcribe` converts a Twi audio file to English text with `provider = "seamless_m4t"`.
- `SeamlessM4TProvider.translate` translates an Ewe sentence to English and preserves a term in `preserve_terms`.
- `SeamlessM4TProvider.synthesize_speech` returns an audio URL for a Twi text input.
- `NLLB200Provider.translate` translates a Dagbani sentence to English when SM4T does not support Dagbani T2T.
- `NLLB200Provider.batch_translate` translates 10 sentences in one call and returns 10 results.
- `select_transcription_provider("ak-GH", ...)` returns `"seamless_m4t"` when SM4T is enabled.
- `select_translation_provider("ee-GH", "en", ...)` returns `"seamless_m4t"` when available.
- `select_translation_provider("nzi-GH", "en", ...)` returns `"nllb_200"` when SM4T does not support Nzema.
- Both sidecar services pass their Docker healthcheck after startup.
- `GET /api/localization/languages` returns an entry for `ak-GH` with `transcription: true`, `translation: true`, `speech: true` when SM4T is running.
- Protected terms in `preserve_terms` survive round-trip translation (source -> English -> source) intact.
- When both sidecars are down, provider selection falls back to cloud and logs a warning; it does not crash.
- Language codes not in the mapping table return `None` from `bcp47_to_sm4t` and `bcp47_to_nllb` without raising an exception.
