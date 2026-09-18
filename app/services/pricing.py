from pydantic import BaseModel


class PricingEstimate(BaseModel):
    destination: str
    days: int
    total_budget: float
    currency: str = "USD"
    daily_budget: float
    lodging: float
    food: float
    activities: float
    local_transport: float
    buffer: float
    trip_style: str


STYLE_ALLOCATIONS = {
    "budget": {
        "lodging": 0.35,
        "food": 0.20,
        "activities": 0.15,
        "local_transport": 0.15,
        "buffer": 0.15,
    },
    "standard": {
        "lodging": 0.40,
        "food": 0.20,
        "activities": 0.18,
        "local_transport": 0.10,
        "buffer": 0.12,
    },
    "luxury": {
        "lodging": 0.55,
        "food": 0.20,
        "activities": 0.15,
        "local_transport": 0.05,
        "buffer": 0.05,
    },
    "adventure": {
        "lodging": 0.30,
        "food": 0.20,
        "activities": 0.30,
        "local_transport": 0.10,
        "buffer": 0.10,
    },
    "family": {
        "lodging": 0.40,
        "food": 0.25,
        "activities": 0.20,
        "local_transport": 0.10,
        "buffer": 0.05,
    },
}


def estimate_trip_cost(
    destination: str,
    days: int,
    budget: float,
    trip_style: str,
) -> PricingEstimate:
    """Estimate how a total trip budget can be distributed across categories."""

    if days < 1:
        raise ValueError("Trip duration must be at least one day.")

    if budget < 0:
        raise ValueError("Trip budget cannot be negative.")

    normalized_style = trip_style.strip().lower()
    allocations = STYLE_ALLOCATIONS.get(
        normalized_style,
        STYLE_ALLOCATIONS["standard"],
    )

    estimate = {
        category: round(budget * percentage, 2)
        for category, percentage in allocations.items()
    }

    return PricingEstimate(
        destination=destination,
        days=days,
        total_budget=round(budget, 2),
        daily_budget=round(budget / days, 2),
        trip_style=normalized_style,
        **estimate,
    )
