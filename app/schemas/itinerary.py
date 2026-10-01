from typing import Optional

from pydantic import BaseModel, Field


class ItineraryActivity(BaseModel):
    name: str = Field(..., min_length=1)
    notes: Optional[str] = None


class ItineraryDay(BaseModel):
    day: int = Field(..., ge=1)
    weather: Optional[str] = None
    activities: list[ItineraryActivity]


class ItineraryCreate(BaseModel):
    trip_id: int
    days: list[ItineraryDay]


class ItineraryPlan(BaseModel):
    days: list[ItineraryDay]


class ItineraryGenerateAI(BaseModel):
    trip_id: int = Field(
        ...,
        description="ID of the trip for which to generate an itinerary",
    )
    request: str | None = Field(
        default=None,
        max_length=2000,
        description="Additional travel preferences or constraints",
    )

class ItineraryResponse(BaseModel):
    trip_id: int
    itinerary: list[ItineraryDay]
    message: str
    ai_generated: bool = False
