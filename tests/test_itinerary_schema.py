import pytest
from pydantic import ValidationError

from app.schemas.itinerary import ItineraryCreate, ItineraryPlan


def test_manual_itinerary_allows_custom_activity_count():
    itinerary = ItineraryCreate.model_validate(
        {
            "trip_id": 1,
            "days": [
                {
                    "day": 1,
                    "activities": [{"name": "Custom activity"}],
                }
            ],
        }
    )

    assert len(itinerary.days[0].activities) == 1


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
                        },
                        {"name": "Louvre"},
                        {"name": "Seine river walk"},
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
                            },
                            {"name": "Louvre"},
                            {"name": "Seine river walk"},
                        ],
                    }
                ]
            }
        )


def test_itinerary_plan_rejects_blank_activity_name():
    with pytest.raises(ValidationError):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "activities": [
                            {"name": "   "},
                            {"name": "Louvre"},
                            {"name": "Seine river walk"},
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
                            },
                            {"name": "Louvre"},
                            {"name": "Seine river walk"},
                        ],
                    }
                ]
            }
        )


def test_itinerary_plan_rejects_too_few_activities():
    with pytest.raises(ValidationError):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "activities": [
                            {"name": "Eiffel Tower"},
                            {"name": "Louvre"},
                        ],
                    }
                ]
            }
        )


def test_itinerary_plan_rejects_too_many_activities():
    with pytest.raises(ValidationError):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "activities": [
                            {"name": f"Activity {number}"}
                            for number in range(1, 7)
                        ],
                    }
                ]
            }
        )


def test_itinerary_plan_requires_sequential_day_numbers():
    with pytest.raises(ValidationError, match="numbered sequentially"):
        ItineraryPlan.model_validate(
            {
                "days": [
                    {
                        "day": 1,
                        "activities": [
                            {"name": f"Day 1 activity {number}"}
                            for number in range(1, 4)
                        ],
                    },
                    {
                        "day": 3,
                        "activities": [
                            {"name": f"Day 3 activity {number}"}
                            for number in range(1, 4)
                        ],
                    },
                ]
            }
        )
