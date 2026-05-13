from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth, users, trips, itineraries

# import models so SQLAlchemy registers them before creating tables
import app.models.user
import app.models.trip
import app.models.itinerary

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Vacation Planner",
    description="Backend API for planning trips and managing itineraries",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itineraries.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "AI Vacation Planner API is running"}
