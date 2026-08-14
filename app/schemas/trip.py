from typing import Optional

from pydantic import BaseModel
from datetime import datetime


class TripCreate(BaseModel):
    destination: str
    days: int
    budget: float
    trip_style: str


class TripUpdate(BaseModel):
    destination: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[float] = None
    trip_style: Optional[str] = None


class TripResponse(BaseModel):
    id: int
    destination: str
    days: int
    budget: float
    trip_style: str
    created_at: datetime

    model_config = {"from_attributes": True}
