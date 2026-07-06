"""Bridge to the built-in TTS tool for dynamic voice segments."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from keprix.voice_templates.audio_utils import TARGET_SAMPLE_RATE, validate_wav_format

logger = logging.getLogger(__name__)

# Languages where cloud/local TTS is considered acceptable when no template exists.
_TTS_SUPPORTED_PREFIXES = (
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "nl",
    "pl",
    "ja",
    "ko",
    "zh",
    "ar",
    "hi",
    "ru",
    "sv",
    "da",
    "fi",
    "no",
    "tr",
)


def supports_tts(language_code: str) -> bool:
    prefix = language_code.split("-")[0].lower()
    return prefix in _TTS_SUPPORTED_PREFIXES


def synthesize_to_wav(text: str, language_code: str) -> bytes | None:
    """
    Synthesize text to WAV bytes using the configured TTS provider.
    Returns None when synthesis fails or output is not WAV-compatible.
    """
    if not text or not text.strip():
        return None
    try:
        from tools.tts_tool import text_to_speech_tool
    except ImportError:
        logger.debug("TTS tool unavailable for voice template hybrid")
        return None

    with tempfile.TemporaryDirectory(prefix="keprix-voice-template-") as tmp:
        out_wav = Path(tmp) / "segment.wav"
        out_mp3 = Path(tmp) / "segment.mp3"
        result_raw = text_to_speech_tool(text=text.strip(), output_path=str(out_mp3))
        try:
            payload = json.loads(result_raw)
        except json.JSONDecodeError:
            return None
        if not payload.get("success"):
            return None
        file_path = Path(str(payload.get("file_path") or ""))
        if not file_path.exists():
            return None
        if file_path.suffix.lower() == ".wav":
            data = file_path.read_bytes()
        elif file_path.suffix.lower() == ".mp3":
            data = _mp3_to_wav(file_path, out_wav)
        else:
            data = file_path.read_bytes()
        if data is None:
            return None
        try:
            validate_wav_format(data)
        except ValueError:
            return None
        return data


def _mp3_to_wav(mp3_path: Path, wav_path: Path) -> bytes | None:
    """Convert MP3 to 16 kHz mono WAV via ffmpeg when available."""
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.debug("ffmpeg not available; cannot convert TTS MP3 to WAV")
        return None
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(mp3_path),
        "-ac",
        "1",
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-sample_fmt",
        "s16",
        str(wav_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if not wav_path.exists():
        return None
    return wav_path.read_bytes()
