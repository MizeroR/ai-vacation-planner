from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import SessionLocal
from app.main import app
from app.models.trip import Trip
from app.models.user import User
from app.schemas.media import ImageAnalysisResponse
from app.services import image as image_service


def _seed_trip(email: str = "image@example.com"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                username="image-user",
                hashed_password="hashed-password",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        trip = db.query(Trip).filter(Trip.user_id == user.id).first()
        if trip is None:
            trip = Trip(
                user_id=user.id,
                destination="Santorini",
                days=4,
                budget=2200.0,
                trip_style="romantic",
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)

        return user, trip
    finally:
        db.close()


def test_analyze_image_returns_structured_travel_summary(monkeypatch):
    monkeypatch.setattr(
        image_service,
        "analyze_image",
        lambda *args, **kwargs: ImageAnalysisResponse(
            description="A cliffside hotel overlooking the sea.",
            destination="Santorini",
            activities=["sunset dinner", "beach walk"],
        ),
    )

    result = image_service.analyze_image(b"fake-image-bytes", request="Describe the scene")

    assert result.description.startswith("A cliffside hotel")
    assert result.destination == "Santorini"
    assert result.activities == ["sunset dinner", "beach walk"]


def test_trip_image_endpoint_analyzes_upload(monkeypatch):
    user, trip = _seed_trip()
    user_stub = type("UserStub", (), {"id": user.id})()
    app.dependency_overrides[get_current_user] = lambda: user_stub

    monkeypatch.setattr(
        image_service,
        "analyze_image",
        lambda file_bytes, request=None, destination=None: ImageAnalysisResponse(
            description="A picturesque harbor town.",
            destination="Amalfi",
            activities=["harbor stroll", "lemon grove tour"],
        ),
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/trips/{trip.id}/image",
                files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
                data={"request": "Describe the destination vibe"},
            )

        assert response.status_code == 200
        assert response.json()["destination"] == "Amalfi"
        assert response.json()["activities"] == ["harbor stroll", "lemon grove tour"]
    finally:
        app.dependency_overrides.clear()
