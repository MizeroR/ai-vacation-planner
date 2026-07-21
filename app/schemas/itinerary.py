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
    trip_id: int


class ItineraryResponse(BaseModel):
    trip_id: int
    itinerary: list[ItineraryDay]
    message: str
    ai_generated: bool = False
