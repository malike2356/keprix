from keprix.voice.vad import VoiceActivityDetector


def test_vad_detects_speech_like_audio() -> None:
    vad = VoiceActivityDetector()

    assert vad.is_speech(b"book a viewing Tuesday")
    assert not vad.is_speech(b"\x80" * 20)
    assert not vad.is_speech(b"")
