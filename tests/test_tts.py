from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import SessionLocal
from app.main import app
from app.models.trip import Trip
from app.models.user import User
from app.schemas.media import AudioResponse
from app.services import tts


def _seed_trip(email: str = "tts@example.com"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                username="tts-user",
                hashed_password="hashed-password",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        trip = db.query(Trip).filter(Trip.user_id == user.id).first()
        if trip is None:
            trip = Trip(
                user_id=user.id,
                destination="Rome",
                days=3,
                budget=1800.0,
                trip_style="culture",
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)

        return user, trip
    finally:
        db.close()


def test_generate_audio_returns_metadata(monkeypatch):
    class FakeEngine:
        def save_to_file(self, text, path):
            self.saved_text = text
            self.path = path
            output = path
            with open(output, "wb") as fh:
                fh.write(b"audio-bytes")

        def runAndWait(self):
            return None

    fake_engine = FakeEngine()
    monkeypatch.setattr(tts, "get_tts_engine", lambda: fake_engine)

    result = tts.generate_audio("Plan my Rome itinerary")

    assert isinstance(result, AudioResponse)
    assert result.filename.endswith(".mp3")
    assert result.media_type in {"audio/mpeg", "audio/mp3"}
    assert fake_engine.saved_text == "Plan my Rome itinerary"


def test_trip_voice_response_endpoint_generates_audio(monkeypatch):
    user, trip = _seed_trip()
    user_stub = type("UserStub", (), {"id": user.id})()
    app.dependency_overrides[get_current_user] = lambda: user_stub

    monkeypatch.setattr(
        tts,
        "generate_audio",
        lambda text, output_dir=None: AudioResponse(
            media_type="audio/mpeg",
            filename="trip-response.mp3",
        ),
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/trips/{trip.id}/voice/response",
                data={"text": "Welcome to Rome with a museum day."},
            )

        assert response.status_code == 200
        assert response.json()["filename"] == "trip-response.mp3"
        assert response.json()["media_type"] == "audio/mpeg"
    finally:
        app.dependency_overrides.clear()
