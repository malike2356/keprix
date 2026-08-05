"""Push-to-talk voice capture for the TUI (Prompt 206)."""

from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from typing import Protocol


MAX_RECORD_SECONDS = 120
SAMPLE_RATE = 16_000
CHANNELS = 1


class VoiceCaptureError(Exception):
    """Voice recording or encoding failed."""


@dataclass
class VoiceCaptureResult:
    data_url: str
    mime_type: str = "audio/wav"


def voice_backend_available() -> bool:
    """Return True when a supported capture backend exists."""
    if shutil.which("arecord"):
        return True
    if shutil.which("ffmpeg"):
        return True
    try:
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401

        return True
    except ImportError:
        return False


def voice_backend_label() -> str:
    if voice_backend_available():
        return "available"
    return "missing (pip install 'keprix[tui-voice]' or install arecord/ffmpeg)"


class VoiceRecorder:
    """Toggle recording with optional sounddevice or arecord/ffmpeg fallback."""

    def __init__(self) -> None:
        self._recording = False
        self._process: subprocess.Popen[bytes] | None = None
        self._temp_path: str | None = None
        self._sounddevice_frames: list[bytes] | None = None
        self._stream = None

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording:
            return
        if _sounddevice_ready():
            self._start_sounddevice()
            return
        if shutil.which("arecord"):
            self._start_arecord()
            return
        if shutil.which("ffmpeg"):
            self._start_ffmpeg()
            return
        raise VoiceCaptureError(
            "Voice capture unavailable. Install arecord/ffmpeg or pip install 'keprix[tui-voice]'."
        )

    def stop(self) -> VoiceCaptureResult:
        if not self._recording:
            raise VoiceCaptureError("Not recording.")
        if self._stream is not None:
            return self._stop_sounddevice()
        if self._process is not None:
            return self._stop_subprocess()
        self._recording = False
        raise VoiceCaptureError("Recording state is invalid.")

    def _start_arecord(self) -> None:
        fd, path = tempfile.mkstemp(prefix="keprix-voice-", suffix=".wav")
        os.close(fd)
        self._temp_path = path
        self._process = subprocess.Popen(
            [
                "arecord",
                "-q",
                "-f",
                "S16_LE",
                "-r",
                str(SAMPLE_RATE),
                "-c",
                str(CHANNELS),
                path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._recording = True

    def _start_ffmpeg(self) -> None:
        fd, path = tempfile.mkstemp(prefix="keprix-voice-", suffix=".wav")
        os.close(fd)
        self._temp_path = path
        self._process = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-f",
                "alsa",
                "-i",
                "default",
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                str(CHANNELS),
                path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._recording = True

    def _start_sounddevice(self) -> None:
        import numpy as np
        import sounddevice as sd

        self._sounddevice_frames = []
        block = int(SAMPLE_RATE * 0.25)

        def _callback(indata, frames, time_info, status) -> None:  # type: ignore[no-untyped-def]
            _ = (frames, time_info, status)
            self._sounddevice_frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=block,
            callback=_callback,
        )
        self._stream.start()
        self._recording = True

    def _stop_sounddevice(self) -> VoiceCaptureResult:
        import numpy as np

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        frames = self._sounddevice_frames or []
        self._sounddevice_frames = None
        self._recording = False
        if not frames:
            raise VoiceCaptureError("Recording is empty.")
        audio = np.concatenate(frames, axis=0)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        payload = buffer.getvalue()
        return _encode_wav(payload)

    def _stop_subprocess(self) -> VoiceCaptureResult:
        process = self._process
        path = self._temp_path
        self._process = None
        self._temp_path = None
        self._recording = False
        if process is None or path is None:
            raise VoiceCaptureError("Recording state is invalid.")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        try:
            payload = open(path, "rb").read()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        if not payload:
            raise VoiceCaptureError("Recording is empty.")
        return _encode_wav(payload)


def _sounddevice_ready() -> bool:
    try:
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401

        return True
    except ImportError:
        return False


def _encode_wav(payload: bytes) -> VoiceCaptureResult:
    encoded = base64.b64encode(payload).decode("ascii")
    return VoiceCaptureResult(data_url=f"data:audio/wav;base64,{encoded}", mime_type="audio/wav")


class TranscribeClient(Protocol):
    async def transcribe_audio(self, data_url: str, *, mime_type: str) -> str: ...
