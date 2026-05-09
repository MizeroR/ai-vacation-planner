from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from app.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    destination = Column(String, nullable=False)
    days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    trip_style = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
