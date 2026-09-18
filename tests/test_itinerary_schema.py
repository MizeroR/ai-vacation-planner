import pytest
from pydantic import ValidationError

from app.schemas.itinerary import ItineraryPlan


def test_itinerary_plan_accepts_valid_days():
    plan = ItineraryPlan.model_validate(
        {
            "days": [
                {
                    "day": 1,
                    "weather": "clear",
                    "activities": [
                        {
                            "name": "Eiffel Tower",
                            "notes": "Visit in the morning",
                        }
                    ],
                }
            ]
        }
    )

    assert len(plan.days) == 1
    assert plan.days[0].activities[0].name == "Eiffel Tower"


def test_itinerary_plan_rejects_activity_without_name():
    with pytest.raises(ValidationError):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "activities": [
                            {
                                "notes": "Missing activity name",
                            }
                        ],
                    }
                ]
            }
        )


def test_itinerary_plan_rejects_day_number_below_one():
    with pytest.raises(ValidationError):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 0,
                        "activities": [
                            {
                                "name": "Invalid day",
                            }
                        ],
                    }
                ]
            }
        )
