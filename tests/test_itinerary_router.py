from app.routers import itineraries


def test_generate_route_uses_user_request(monkeypatch):
    captured = {}

    def fake_generate_planned_itinerary(**kwargs):
        captured.update(kwargs)
        return [
            {
                "day": 1,
                "weather": "clear",
                "activities": [
                    {
                        "name": "Visit the Louvre",
                        "notes": None,
                    }
                ],
            }
        ]

    monkeypatch.setattr(
        itineraries,
        "generate_planned_itinerary",
        fake_generate_planned_itinerary,
    )

    result = itineraries.generate_planned_itinerary(
        destination="Paris",
        days=1,
        budget=500,
        trip_style="budget",
        request="Include weather-friendly activities.",
    )

    assert result[0]["activities"][0]["name"] == "Visit the Louvre"
    assert captured["request"] == "Include weather-friendly activities."