from collections.abc import Iterable
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from app.config import settings
from app.schemas.media import SpeechResponse


class SpeechToTextError(Exception):
    """Raised when audio transcription fails."""


_model: WhisperModel | None = None


def get_speech_model() -> WhisperModel:
    global _model

    if _model is None:
        _model = WhisperModel(
            settings.stt_model,
            device="cpu",
            compute_type="int8",
        )

    return _model


def _combine_segments(segments: Iterable[Any]) -> str:
    parts = []

    for segment in segments:
        text = getattr(segment, "text", "")
        if text:
            parts.append(text.strip())

    return " ".join(parts).strip()


def transcribe_audio(audio_path: str | Path) -> SpeechResponse:
    """Transcribe a local audio file with faster-whisper."""

    path = Path(audio_path)

    if not path.exists():
        raise SpeechToTextError("The audio file could not be found.")

    if not path.is_file():
        raise SpeechToTextError("The audio path is not a file.")

    try:
        segments, information = get_speech_model().transcribe(
            str(path),
            beam_size=5,
            vad_filter=True,
        )
        text = _combine_segments(segments)

        if not text:
            raise SpeechToTextError(
                "No speech could be detected in the audio file."
            )

        return SpeechResponse(
            text=text,
            language=getattr(information, "language", None),
        )
    except SpeechToTextError:
        raise
    except Exception as exc:
        raise SpeechToTextError(
            "The audio file could not be transcribed."
        ) from exc
