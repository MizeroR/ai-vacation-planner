from app.schemas.itinerary import ItineraryGenerateAI


def test_itinerary_generate_request_accepts_trip_id_only():
    request = ItineraryGenerateAI.model_validate({"trip_id": 1})

    assert request.trip_id == 1
    assert request.request is None


def test_itinerary_generate_request_accepts_custom_request():
    request = ItineraryGenerateAI.model_validate(
        {
            "trip_id": 1,
            "request": "Include weather-friendly activities.",
        }
    )

    assert request.trip_id == 1
    assert request.request == "Include weather-friendly activities."


def test_itinerary_generate_request_rejects_long_request():
    long_request = "a" * 2001

    try:
        ItineraryGenerateAI.model_validate(
            {
                "trip_id": 1,
                "request": long_request,
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected validation failure for an oversized request")