"""WAV validation and concatenation (16 kHz, 16-bit mono)."""

from __future__ import annotations

import io
import struct
import wave
from typing import Iterable

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2  # 16-bit
MIN_DURATION_SECONDS = 0.5
MAX_DURATION_SECONDS = 30.0


class AudioFormatError(ValueError):
    pass


def get_audio_duration(audio_bytes: bytes) -> float:
    """Return duration in seconds for a WAV clip."""
    params = _read_wav_params(audio_bytes)
    if params["nframes"] == 0 or params["framerate"] == 0:
        return 0.0
    return params["nframes"] / params["framerate"]


def validate_wav_format(audio_bytes: bytes) -> float:
    """
    Validate WAV is 16 kHz, 16-bit mono and within duration limits.
    Returns duration in seconds.
    """
    if len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF" or audio_bytes[8:12] != b"WAVE":
        raise AudioFormatError("File must be a WAV (RIFF/WAVE) audio clip")

    params = _read_wav_params(audio_bytes)
    if params["nchannels"] != TARGET_CHANNELS:
        raise AudioFormatError(f"WAV must be mono ({TARGET_CHANNELS} channel)")
    if params["sampwidth"] != TARGET_SAMPLE_WIDTH:
        raise AudioFormatError("WAV must be 16-bit PCM")
    if params["framerate"] != TARGET_SAMPLE_RATE:
        raise AudioFormatError(f"WAV must be {TARGET_SAMPLE_RATE} Hz")

    duration = get_audio_duration(audio_bytes)
    if duration < MIN_DURATION_SECONDS:
        raise AudioFormatError(f"Recording must be at least {MIN_DURATION_SECONDS}s")
    if duration > MAX_DURATION_SECONDS:
        raise AudioFormatError(f"Recording must be at most {MAX_DURATION_SECONDS}s")
    return duration


def generate_silence_wav(gap_ms: int, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Generate silence as a WAV byte string."""
    frame_count = int(sample_rate * (gap_ms / 1000.0))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(TARGET_CHANNELS)
        wf.setsampwidth(TARGET_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def concatenate_audio(audio1: bytes, audio2: bytes, gap_ms: int = 400) -> bytes:
    """Concatenate two WAV clips with a silence gap (same format required)."""
    validate_wav_format(audio1)
    validate_wav_format(audio2)
    silence = generate_silence_wav(gap_ms)
    return combine_wav_bytes([audio1, silence, audio2])


def combine_wav_bytes(chunks: Iterable[bytes]) -> bytes:
    """Combine multiple same-format WAV byte strings into one."""
    frames: list[bytes] = []
    params: dict[str, int] | None = None
    for chunk in chunks:
        parsed = _read_wav_params(chunk)
        if params is None:
            params = {
                "nchannels": parsed["nchannels"],
                "sampwidth": parsed["sampwidth"],
                "framerate": parsed["framerate"],
            }
        else:
            if (
                parsed["nchannels"] != params["nchannels"]
                or parsed["sampwidth"] != params["sampwidth"]
                or parsed["framerate"] != params["framerate"]
            ):
                raise AudioFormatError("All WAV clips must share sample rate, width, and channels")
        frames.append(parsed["frames"])

    assert params is not None
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(params["nchannels"])
        wf.setsampwidth(params["sampwidth"])
        wf.setframerate(params["framerate"])
        for frame in frames:
            wf.writeframes(frame)
    return out.getvalue()


def _read_wav_params(audio_bytes: bytes) -> dict[str, int | bytes]:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        return {
            "nchannels": wf.getnchannels(),
            "sampwidth": wf.getsampwidth(),
            "framerate": wf.getframerate(),
            "nframes": wf.getnframes(),
            "frames": wf.readframes(wf.getnframes()),
        }


def make_test_wav(duration_seconds: float = 1.0, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Build a minimal valid mono WAV for tests."""
    nframes = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(TARGET_CHANNELS)
        wf.setsampwidth(TARGET_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x01" * nframes)
    return buffer.getvalue()
