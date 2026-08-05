"""GUI-writable speech-to-text / voice input settings."""

from __future__ import annotations

from typing import Any

from keprix.api.provider_settings import persist_env_value, remove_env_value
from keprix.api.stt_config import max_recording_seconds, stt_enabled, stt_provider, stt_section

STT_PROVIDERS: tuple[dict[str, Any], ...] = (
    {
        "id": "local",
        "label": "Local (faster-whisper)",
        "badge": "Free",
        "description": "Runs on the server. No API key. Model downloads on first use.",
        "env_key": None,
        "needs_key": False,
        "key_url": None,
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "badge": "Cloud",
        "description": "Gemini multimodal audio transcription (uses GEMINI_API_KEY or GOOGLE_API_KEY).",
        "env_key": "GEMINI_API_KEY",
        "needs_key": True,
        "alt_env_keys": ("GOOGLE_API_KEY",),
        "key_url": "https://aistudio.google.com/app/apikey",
    },
    {
        "id": "groq",
        "label": "Groq Whisper",
        "badge": "Free tier",
        "description": "Cloud Whisper via Groq.",
        "env_key": "GROQ_API_KEY",
        "needs_key": True,
        "key_url": "https://console.groq.com/keys",
    },
    {
        "id": "openai",
        "label": "OpenAI Whisper",
        "badge": "Paid",
        "description": "OpenAI audio transcription API.",
        "env_key": "VOICE_TOOLS_OPENAI_KEY",
        "needs_key": True,
        "alt_env_keys": ("OPENAI_API_KEY",),
        "key_url": "https://platform.openai.com/api-keys",
    },
    {
        "id": "mistral",
        "label": "Mistral Voxtral",
        "badge": "Cloud",
        "description": "Mistral speech-to-text.",
        "env_key": "MISTRAL_API_KEY",
        "needs_key": True,
        "key_url": "https://console.mistral.ai/api-keys",
    },
    {
        "id": "xai",
        "label": "xAI Grok STT",
        "badge": "Cloud",
        "description": "xAI speech-to-text.",
        "env_key": "XAI_API_KEY",
        "needs_key": True,
        "key_url": "https://console.x.ai/",
    },
    {
        "id": "elevenlabs",
        "label": "ElevenLabs Scribe",
        "badge": "Cloud",
        "description": "ElevenLabs Scribe transcription.",
        "env_key": "ELEVENLABS_API_KEY",
        "needs_key": True,
        "key_url": "https://elevenlabs.io/app/settings/api-keys",
    },
)

LOCAL_MODELS = ("tiny", "base", "small", "medium", "large-v3")
OPENAI_MODELS = ("whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe")
MISTRAL_MODELS = ("voxtral-mini-latest", "voxtral-mini-2602")
ELEVENLABS_MODELS = ("scribe_v2", "scribe_v1")
GROQ_MODELS = ("whisper-large-v3-turbo", "whisper-large-v3")
GEMINI_MODELS = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash")


def _env_configured(key: str) -> bool:
    try:
        from keprix_cli.config import get_env_value

        value = get_env_value(key)
    except Exception:
        value = None
    if value is None:
        import os

        value = os.getenv(key, "")
    return bool(str(value or "").strip())


def _provider_key_ready(provider: dict[str, Any]) -> bool:
    if not provider.get("needs_key"):
        return True
    keys = [provider.get("env_key"), *list(provider.get("alt_env_keys") or [])]
    return any(key and _env_configured(str(key)) for key in keys)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def voice_settings_snapshot() -> dict[str, Any]:
    stt = stt_section()
    local = _as_dict(stt.get("local"))
    openai = _as_dict(stt.get("openai"))
    mistral = _as_dict(stt.get("mistral"))
    elevenlabs = _as_dict(stt.get("elevenlabs"))
    groq = _as_dict(stt.get("groq"))
    gemini = _as_dict(stt.get("gemini"))
    provider = str(stt.get("provider") or "local")
    if provider == "google":
        provider = "gemini"
    enabled = stt_enabled()
    catalog = []
    for row in STT_PROVIDERS:
        catalog.append(
            {
                **row,
                "has_api_key": _provider_key_ready(row),
                "is_active": provider == row["id"] and enabled,
            }
        )
    return {
        "enabled": enabled,
        "provider": provider if enabled else None,
        "configured_provider": provider,
        "max_recording_seconds": max_recording_seconds(),
        "transcribe_path": "/api/audio/transcribe",
        "local_model": str(local.get("model") or "base"),
        "local_language": str(local.get("language") or ""),
        "openai_model": str(openai.get("model") or "whisper-1"),
        "mistral_model": str(mistral.get("model") or "voxtral-mini-latest"),
        "elevenlabs_model": str(elevenlabs.get("model_id") or "scribe_v2"),
        "groq_model": str(groq.get("model") or "whisper-large-v3-turbo"),
        "gemini_model": str(gemini.get("model") or "gemini-2.5-flash"),
        "auto_tts": bool(_load_voice_section().get("auto_tts", False)),
        "beep_enabled": bool(_load_voice_section().get("beep_enabled", True)),
        "catalog": catalog,
        "options": {
            "local_models": list(LOCAL_MODELS),
            "openai_models": list(OPENAI_MODELS),
            "mistral_models": list(MISTRAL_MODELS),
            "elevenlabs_models": list(ELEVENLABS_MODELS),
            "groq_models": list(GROQ_MODELS),
            "gemini_models": list(GEMINI_MODELS),
            "providers": [row["id"] for row in STT_PROVIDERS],
        },
        # camelCase mirrors for UI convenience
        "maxRecordingSeconds": max_recording_seconds(),
        "transcribePath": "/api/audio/transcribe",
        "localModel": str(local.get("model") or "base"),
        "localLanguage": str(local.get("language") or ""),
        "openaiModel": str(openai.get("model") or "whisper-1"),
        "mistralModel": str(mistral.get("model") or "voxtral-mini-latest"),
        "elevenlabsModel": str(elevenlabs.get("model_id") or "scribe_v2"),
        "groqModel": str(groq.get("model") or "whisper-large-v3-turbo"),
        "geminiModel": str(gemini.get("model") or "gemini-2.5-flash"),
        "autoTts": bool(_load_voice_section().get("auto_tts", False)),
        "beepEnabled": bool(_load_voice_section().get("beep_enabled", True)),
        "configuredProvider": provider,
    }


def _load_voice_section() -> dict[str, Any]:
    try:
        from keprix_cli.config import load_config

        voice = load_config().get("voice")
        return voice if isinstance(voice, dict) else {}
    except Exception:
        return {}


def update_voice_settings(payload: dict[str, Any]) -> dict[str, Any]:
    from keprix_cli.config import load_config, save_config

    cfg = load_config()
    if not isinstance(cfg, dict):
        cfg = {}

    stt = cfg.get("stt")
    if not isinstance(stt, dict):
        stt = {}
        cfg["stt"] = stt
    voice = cfg.get("voice")
    if not isinstance(voice, dict):
        voice = {}
        cfg["voice"] = voice

    if "enabled" in payload and payload["enabled"] is not None:
        stt["enabled"] = bool(payload["enabled"])

    provider = payload.get("provider") or payload.get("configuredProvider")
    if provider is not None:
        provider_id = str(provider).strip().lower()
        if provider_id == "google":
            provider_id = "gemini"
        known = {row["id"] for row in STT_PROVIDERS}
        if provider_id not in known:
            raise ValueError(f"Unknown STT provider: {provider_id}")
        stt["provider"] = provider_id

    if "max_recording_seconds" in payload or "maxRecordingSeconds" in payload:
        raw = payload.get("max_recording_seconds", payload.get("maxRecordingSeconds"))
        seconds = int(raw)
        voice["max_recording_seconds"] = max(5, min(seconds, 600))

    if "auto_tts" in payload or "autoTts" in payload:
        voice["auto_tts"] = bool(payload.get("auto_tts", payload.get("autoTts")))

    if "beep_enabled" in payload or "beepEnabled" in payload:
        voice["beep_enabled"] = bool(payload.get("beep_enabled", payload.get("beepEnabled")))

    local = stt.setdefault("local", {})
    if not isinstance(local, dict):
        local = {}
        stt["local"] = local
    if "local_model" in payload or "localModel" in payload:
        model = str(payload.get("local_model", payload.get("localModel")) or "base").strip()
        local["model"] = model if model in LOCAL_MODELS else "base"
    if "local_language" in payload or "localLanguage" in payload:
        local["language"] = str(payload.get("local_language", payload.get("localLanguage")) or "").strip()

    openai = stt.setdefault("openai", {})
    if not isinstance(openai, dict):
        openai = {}
        stt["openai"] = openai
    if "openai_model" in payload or "openaiModel" in payload:
        model = str(payload.get("openai_model", payload.get("openaiModel")) or "whisper-1").strip()
        openai["model"] = model if model in OPENAI_MODELS else "whisper-1"

    mistral = stt.setdefault("mistral", {})
    if not isinstance(mistral, dict):
        mistral = {}
        stt["mistral"] = mistral
    if "mistral_model" in payload or "mistralModel" in payload:
        model = str(payload.get("mistral_model", payload.get("mistralModel")) or "voxtral-mini-latest").strip()
        mistral["model"] = model if model in MISTRAL_MODELS else "voxtral-mini-latest"

    elevenlabs = stt.setdefault("elevenlabs", {})
    if not isinstance(elevenlabs, dict):
        elevenlabs = {}
        stt["elevenlabs"] = elevenlabs
    if "elevenlabs_model" in payload or "elevenlabsModel" in payload:
        model = str(payload.get("elevenlabs_model", payload.get("elevenlabsModel")) or "scribe_v2").strip()
        elevenlabs["model_id"] = model if model in ELEVENLABS_MODELS else "scribe_v2"

    groq = stt.setdefault("groq", {})
    if not isinstance(groq, dict):
        groq = {}
        stt["groq"] = groq
    if "groq_model" in payload or "groqModel" in payload:
        model = str(payload.get("groq_model", payload.get("groqModel")) or "whisper-large-v3-turbo").strip()
        groq["model"] = model if model in GROQ_MODELS else "whisper-large-v3-turbo"

    gemini = stt.setdefault("gemini", {})
    if not isinstance(gemini, dict):
        gemini = {}
        stt["gemini"] = gemini
    if "gemini_model" in payload or "geminiModel" in payload:
        model = str(payload.get("gemini_model", payload.get("geminiModel")) or "gemini-2.5-flash").strip()
        gemini["model"] = model if model in GEMINI_MODELS else "gemini-2.5-flash"

    # Optional API key updates (never echoed back)
    api_keys = payload.get("api_keys") or payload.get("apiKeys") or {}
    if isinstance(api_keys, dict):
        for row in STT_PROVIDERS:
            env_key = row.get("env_key")
            if not env_key:
                continue
            if env_key not in api_keys and row["id"] not in api_keys:
                continue
            value = api_keys.get(env_key, api_keys.get(row["id"]))
            if value is None:
                continue
            text = str(value).strip()
            if text == "":
                remove_env_value(str(env_key))
            else:
                persist_env_value(str(env_key), text)

    clear_key_for = payload.get("clear_api_key_for") or payload.get("clearApiKeyFor")
    if clear_key_for:
        target = str(clear_key_for).strip().lower()
        if target == "google":
            target = "gemini"
        for row in STT_PROVIDERS:
            if row["id"] != target:
                continue
            keys = [row.get("env_key"), *list(row.get("alt_env_keys") or [])]
            for key in keys:
                if key:
                    remove_env_value(str(key))
            break

    save_config(cfg)
    return voice_settings_snapshot()
