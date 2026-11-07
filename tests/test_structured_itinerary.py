from app.schemas.itinerary import ItineraryPlan
from app.services import llm


class FakeStructuredModel:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_structured_model_returns_valid_itinerary(monkeypatch):
    expected_plan = ItineraryPlan.model_validate(
        {
            "days": [
                {
                    "day": 1,
                    "weather": "clear",
                    "activities": [
                        {
                            "name": "Visit the Eiffel Tower",
                            "notes": "Go in the morning",
                        },
                        {"name": "Visit the Louvre"},
                        {"name": "Walk along the Seine"},
                    ],
                }
            ]
        }
    )

    fake_model = FakeStructuredModel(expected_plan)

    monkeypatch.setattr(
        llm,
        "get_structured_model",
        lambda: fake_model,
    )
    monkeypatch.setattr(
        llm,
        "lookup_weather_context",
        lambda destination: None,
    )
    monkeypatch.setattr(
        llm.kb,
        "query",
        lambda query, top_k: [],
    )

    result = llm.generate_itinerary(
        destination="Paris",
        days=1,
        budget=500,
        trip_style="budget",
    )

    assert result == [
        {
            "day": 1,
            "weather": "clear",
            "activities": [
                {
                    "name": "Visit the Eiffel Tower",
                    "notes": "Go in the morning",
                },
                {"name": "Visit the Louvre", "notes": None},
                {"name": "Walk along the Seine", "notes": None},
            ],
        }
    ]


def test_structured_model_retries_after_failure(monkeypatch):
    expected_plan = ItineraryPlan.model_validate(
        {
            "days": [
                {
                    "day": 1,
                    "weather": None,
                    "activities": [
                        {
                            "name": "Visit a museum",
                            "notes": None,
                        },
                        {"name": "Walk through a garden"},
                        {"name": "Try local food"},
                    ],
                }
            ]
        }
    )

    class RetryModel:
        def __init__(self):
            self.calls = 0

        def invoke(self, prompt):
            self.calls += 1

            if self.calls == 1:
                raise ValueError("temporary structured output failure")

            return expected_plan

    fake_model = RetryModel()

    monkeypatch.setattr(
        llm,
        "get_structured_model",
        lambda: fake_model,
    )
    monkeypatch.setattr(
        llm,
        "lookup_weather_context",
        lambda destination: None,
    )
    monkeypatch.setattr(
        llm.kb,
        "query",
        lambda query, top_k: [],
    )

    result = llm.generate_itinerary(
        destination="Paris",
        days=1,
        budget=500,
        trip_style="budget",
    )

    assert fake_model.calls == 2
    assert result[0]["activities"][0]["name"] == "Visit a museum"


def test_structured_model_retries_after_duration_mismatch(monkeypatch):
    one_day_plan = ItineraryPlan.model_validate(
        {
            "days": [
                {
                    "day": 1,
                    "activities": [
                        {"name": "Visit a museum"},
                        {"name": "Walk through a garden"},
                        {"name": "Try local food"},
                    ],
                }
            ]
        }
    )
    expected_plan = ItineraryPlan.model_validate(
        {
            "days": [
                {
                    "day": day,
                    "activities": [
                        {"name": f"Day {day} activity {number}"}
                        for number in range(1, 4)
                    ],
                }
                for day in (1, 2)
            ]
        }
    )

    class DurationRetryModel:
        def __init__(self):
            self.responses = [one_day_plan, expected_plan]
            self.prompts = []

        def invoke(self, prompt):
            self.prompts.append(prompt)
            return self.responses[len(self.prompts) - 1]

    fake_model = DurationRetryModel()
    monkeypatch.setattr(llm, "get_structured_model", lambda: fake_model)
    monkeypatch.setattr(llm, "lookup_weather_context", lambda destination: None)
    monkeypatch.setattr(llm.kb, "query", lambda query, top_k: [])

    result = llm.generate_itinerary(
        destination="Paris",
        days=2,
        budget=500,
        trip_style="budget",
    )

    assert len(result) == 2
    assert len(fake_model.prompts) == 2
    assert "previous response failed validation" in fake_model.prompts[1]
