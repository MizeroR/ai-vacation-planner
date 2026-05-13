from pydantic import BaseModel


class ItineraryDay(BaseModel):
    day: int
    activities: list[str]


class ItineraryCreate(BaseModel):
    trip_id: int
    days: list[ItineraryDay]


class ItineraryResponse(BaseModel):
    trip_id: int
    itinerary: list[ItineraryDay]
    message: str
