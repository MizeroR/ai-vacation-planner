from app.schemas.media import (
    ImageAnalysisResponse,
    MultimodalTripRequest,
    SpeechResponse,
    VoiceTripRequest,
)


def test_voice_request_accepts_optional_text():
    request = VoiceTripRequest(
        trip_id=1,
        request="Prefer indoor activities if it rains.",
    )

    assert request.trip_id == 1
    assert request.request == "Prefer indoor activities if it rains."


def test_speech_response_contains_transcribed_text():
    response = SpeechResponse(
        text="Plan a Paris trip with museum activities.",
        language="en",
    )

    assert response.text.startswith("Plan a Paris trip")
    assert response.language == "en"


def test_image_analysis_response_contains_travel_context():
    response = ImageAnalysisResponse(
        description="A museum entrance",
        destination="Paris",
        activities=["museum visit"],
    )

    assert response.destination == "Paris"
    assert response.activities == ["museum visit"]


def test_multimodal_request_accepts_trip_id_only():
    request = MultimodalTripRequest(trip_id=1)

    assert request.trip_id == 1
    assert request.request is None