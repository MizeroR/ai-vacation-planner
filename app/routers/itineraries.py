from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.itinerary import Itinerary
from app.models.trip import Trip
from app.models.user import User
from app.schemas.itinerary import ItineraryCreate, ItineraryGenerateAI, ItineraryResponse
from app.core.dependencies import get_current_user
from app.services.llm import generate_itinerary

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ItineraryResponse)
def create_itinerary(body: ItineraryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == body.trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if db.query(Itinerary).filter(Itinerary.trip_id == body.trip_id).first():
        raise HTTPException(status_code=400, detail="Itinerary already exists for this trip")

    itinerary = Itinerary(
        trip_id=body.trip_id,
        days=[day.model_dump() for day in body.days],
    )
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        itinerary=itinerary.days,
        message="Itinerary created successfully",
    )


@router.get("/{trip_id}", response_model=ItineraryResponse)
def get_itinerary(trip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    itinerary = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="No itinerary found for this trip")

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        itinerary=itinerary.days,
        message="Itinerary retrieved successfully",
    )


@router.post("/generate", status_code=status.HTTP_201_CREATED, response_model=ItineraryResponse)
def generate_ai_itinerary(body: ItineraryGenerateAI, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.query(Trip).filter(Trip.id == body.trip_id, Trip.user_id == current_user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if db.query(Itinerary).filter(Itinerary.trip_id == body.trip_id).first():
        raise HTTPException(status_code=400, detail="Itinerary already exists for this trip")

    # Call Claude to generate itinerary
    ai_generated_days = generate_itinerary(
        destination=trip.destination,
        days=trip.days,
        budget=trip.budget,
        trip_style=trip.trip_style,
    )

    itinerary = Itinerary(
        trip_id=body.trip_id,
        days=ai_generated_days,
    )
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)

    return ItineraryResponse(
        trip_id=itinerary.trip_id,
        itinerary=itinerary.days,
        message="Itinerary generated successfully by AI",
        ai_generated=True,
    )
