import mimetypes
import tempfile
import uuid
from pathlib import Path

from app.config import settings
from app.schemas.media import AudioResponse


class TextToSpeechError(Exception):
    """Raised when text-to-speech synthesis fails."""


_engine = None


def get_tts_engine():
    global _engine

    if _engine is not None:
        return _engine

    try:
        import pyttsx3
    except ImportError as exc:
        raise TextToSpeechError(
            "The local TTS dependency is not installed."
        ) from exc

    try:
        _engine = pyttsx3.init()
    except Exception as exc:
        raise TextToSpeechError(
            "The local TTS engine could not be started."
        ) from exc

    if settings.tts_voice:
        try:
            voices = _engine.getProperty("voices")
            matching_voice = next(
                (
                    voice
                    for voice in voices
                    if getattr(voice, "id", None) == settings.tts_voice
                    or getattr(voice, "name", None) == settings.tts_voice
                ),
                None,
            )
            if matching_voice is not None:
                _engine.setProperty("voice", matching_voice.id)
        except Exception:
            pass

    return _engine


def generate_audio(
    text: str,
    *,
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> AudioResponse:
    """Generate a local audio file from the supplied text."""

    if text is None or not str(text).strip():
        raise TextToSpeechError("Text to speak cannot be empty.")

    cleaned_text = str(text).strip()
    output_root = Path(output_dir) if output_dir is not None else Path(tempfile.gettempdir()) / "ai_vacation_planner"
    output_root.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"speech-{uuid.uuid4().hex}.mp3"

    output_path = output_root / filename
    if output_path.suffix.lower() not in {".mp3", ".wav", ".ogg", ".m4a"}:
        output_path = output_root / f"{output_path.name}.mp3"

    engine = get_tts_engine()

    try:
        engine.save_to_file(cleaned_text, str(output_path))
        engine.runAndWait()
    except Exception as exc:
        raise TextToSpeechError(
            "The speech audio could not be generated."
        ) from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TextToSpeechError(
            "The speech audio could not be generated."
        )

    media_type = mimetypes.guess_type(str(output_path))[0] or "audio/mpeg"
    return AudioResponse(media_type=media_type, filename=output_path.name)


def text_to_speech(*args, **kwargs) -> AudioResponse:
    return generate_audio(*args, **kwargs)


def synthesize_audio(*args, **kwargs) -> AudioResponse:
    return generate_audio(*args, **kwargs)
