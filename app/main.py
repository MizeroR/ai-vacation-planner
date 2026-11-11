from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth, users, trips, itineraries, kb
from app.services.observability import observe_span, record_http_request

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
app.include_router(kb.router)


@app.middleware("http")
async def observe_http_requests(request, call_next):
    request_id = str(uuid4())
    started_at = perf_counter()
    status_code = 500

    with observe_span(
        "vacation_planner.http.request",
        tags={
            "http.method": request.method,
            "http.request_id": request_id,
        },
    ) as span:
        try:
            response = await call_next(request)
            status_code = response.status_code
            route = getattr(request.scope.get("route"), "path", "unmatched")
            duration_seconds = perf_counter() - started_at
            record_http_request(
                method=request.method,
                route=route,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            if span is not None:
                span.set_tag("http.route", route)
                span.set_tag("http.status_code", status_code)
                span.set_tag(
                    "http.outcome",
                    "error"
                    if status_code >= 500
                    else "failed"
                    if status_code >= 400
                    else "success",
                )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_seconds = perf_counter() - started_at
            record_http_request(
                method=request.method,
                route=getattr(request.scope.get("route"), "path", "unmatched"),
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            if span is not None:
                span.set_tag("http.status_code", status_code)
                span.set_tag("http.outcome", "error")
            raise


@app.get("/", tags=["Health"])
def root():
    return {"message": "AI Vacation Planner API is running"}
