import pytest

from app.services.pricing import estimate_trip_cost


def test_pricing_estimate_allocates_full_budget():
    result = estimate_trip_cost(
        destination="Paris",
        days=5,
        budget=1500,
        trip_style="budget",
    )

    categories_total = (
        result.lodging
        + result.food
        + result.activities
        + result.local_transport
        + result.buffer
    )

    assert result.destination == "Paris"
    assert result.daily_budget == 300
    assert categories_total == 1500


def test_unknown_trip_style_uses_standard_allocation():
    result = estimate_trip_cost(
        destination="Tokyo",
        days=4,
        budget=2000,
        trip_style="unknown-style",
    )

    assert result.trip_style == "unknown-style"
    assert result.lodging == 800
    assert result.food == 400


def test_pricing_estimate_rejects_invalid_days():
    with pytest.raises(ValueError, match="at least one day"):
        estimate_trip_cost(
            destination="Paris",
            days=0,
            budget=1000,
            trip_style="budget",
        )


def test_pricing_estimate_rejects_negative_budget():
    with pytest.raises(ValueError, match="cannot be negative"):
        estimate_trip_cost(
            destination="Paris",
            days=3,
            budget=-100,
            trip_style="budget",
        )