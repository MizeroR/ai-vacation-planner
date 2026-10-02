from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import SessionLocal
from app.main import app
from app.models.trip import Trip
from app.models.user import User
from app.services import speech


def _seed_trip(email: str = "voice@example.com"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                username="voice-user",
                hashed_password="hashed-password",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        trip = db.query(Trip).filter(Trip.user_id == user.id).first()
        if trip is None:
            trip = Trip(
                user_id=user.id,
                destination="Lisbon",
                days=3,
                budget=1200.0,
                trip_style="city break",
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)

        return user, trip
    finally:
        db.close()


def test_trip_voice_endpoint_transcribes_upload(monkeypatch):
    user, trip = _seed_trip()
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        speech,
        "transcribe_audio",
        lambda path: speech.SpeechResponse(text="Plan my Lisbon trip", language="en"),
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/trips/{trip.id}/voice",
                files={"file": ("voice.wav", b"audio-bytes", "audio/wav")},
                data={"request": "Include museums and food stops"},
            )

        assert response.status_code == 200
        assert response.json()["text"] == "Plan my Lisbon trip"
        assert response.json()["language"] == "en"
    finally:
        app.dependency_overrides.clear()
