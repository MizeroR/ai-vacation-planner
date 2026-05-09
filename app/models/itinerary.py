from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, func
from app.database import Base


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, unique=True)
    days = Column(JSON, nullable=False)  # stores list of {day, activities}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
