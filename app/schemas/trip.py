from pydantic import BaseModel
from datetime import datetime


class TripCreate(BaseModel):
    destination: str
    days: int
    budget: float
    trip_style: str


class TripUpdate(BaseModel):
    destination: str | None = None
    days: int | None = None
    budget: float | None = None
    trip_style: str | None = None


class TripResponse(BaseModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    created_at: datetime

    model_config = {"from_attributes": True}
