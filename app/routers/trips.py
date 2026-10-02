import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.trip import Trip
from app.models.user import User
from app.schemas.media import SpeechResponse
from app.schemas.trip import TripCreate, TripUpdate, TripResponse
from app.core.dependencies import get_current_user
from app.services import speech
from app.services.speech import SpeechToTextError

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trip(body: TripCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = Trip(**body.model_dump(), user_id=current_user.id)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return {**TripResponse.model_validate(trip).model_dump(), "message": "Trip created successfully"}


@router.get("", response_model=list[TripResponse])
def list_trips(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Trip).filter(Trip.user_id == current_user.id).all()


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(trip_id: int, body: TripUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(trip, field, value)

    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/voice", response_model=SpeechResponse)
def transcribe_trip_voice(
    trip_id: int,
    file: UploadFile = File(...),
    request: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if file.size is not None and file.size > settings.max_audio_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds the {settings.max_audio_upload_bytes} byte limit.",
        )

    content_type = (file.content_type or "").lower()
    allowed_types = {
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/webm",
        "audio/ogg",
    }
    filename = (file.filename or "voice.wav").lower()
    suffix = Path(filename).suffix.lower()
    allowed_suffixes = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".mp4"}

    if content_type not in allowed_types and suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. Please upload WAV, MP3, M4A, OGG, or WEBM audio.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix or ".wav", delete=False) as temp_file:
        while chunk := file.file.read(8192):
            temp_file.write(chunk)
        temp_path = temp_file.name

    try:
        return speech.transcribe_audio(temp_path)
    except SpeechToTextError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        Path(temp_path).unlink(missing_ok=True)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.delete(trip)
    db.commit()
