from types import SimpleNamespace

import pytest

from app.services import speech
from app.schemas.media import SpeechResponse


class FakeSpeechModel:
    def __init__(self, segments=None, information=None, error=None):
        self.segments = segments or []
        self.information = information or SimpleNamespace(language="en")
        self.error = error

    def transcribe(self, path, beam_size, vad_filter):
        if self.error:
            raise self.error

        return iter(self.segments), self.information


def test_transcribe_audio_rejects_missing_file(tmp_path):
    with pytest.raises(speech.SpeechToTextError, match="could not be found"):
        speech.transcribe_audio(tmp_path / "missing.wav")


def test_transcribe_audio_combines_segments(monkeypatch, tmp_path):
    audio_path = tmp_path / "request.wav"
    audio_path.write_bytes(b"audio")

    model = FakeSpeechModel(
        segments=[
            SimpleNamespace(text="Plan my Paris trip"),
            SimpleNamespace(text="with museum activities."),
        ]
    )
    monkeypatch.setattr(speech, "get_speech_model", lambda: model)

    result = speech.transcribe_audio(audio_path)

    assert isinstance(result, SpeechResponse)
    assert result.text == "Plan my Paris trip with museum activities."
    assert result.language == "en"


def test_transcribe_audio_hides_model_failure(monkeypatch, tmp_path):
    audio_path = tmp_path / "request.wav"
    audio_path.write_bytes(b"audio")
    model = FakeSpeechModel(error=RuntimeError("provider details"))
    monkeypatch.setattr(speech, "get_speech_model", lambda: model)

    with pytest.raises(
        speech.SpeechToTextError,
        match="could not be transcribed",
    ) as error:
        speech.transcribe_audio(audio_path)

    assert "provider details" not in str(error.value)
