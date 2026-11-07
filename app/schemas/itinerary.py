from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ItineraryActivity(BaseModel):
    name: str = Field(..., min_length=1)
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Activity name must not be blank.")
        return name


class ItineraryDay(BaseModel):
    day: int = Field(..., ge=1)
    weather: Optional[str] = None
    activities: list[ItineraryActivity]


class ItineraryPlanDay(ItineraryDay):
    activities: list[ItineraryActivity] = Field(min_length=3, max_length=5)


class ItineraryDurationError(ValueError):
    pass


class ItineraryCreate(BaseModel):
    trip_id: int
    days: list[ItineraryDay]


class ItineraryPlan(BaseModel):
    days: list[ItineraryPlanDay] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sequential_days(self):
        expected_days = list(range(1, len(self.days) + 1))
        actual_days = [day.day for day in self.days]

        if actual_days != expected_days:
            raise ValueError("Itinerary days must be numbered sequentially from 1.")

        return self

    def validate_duration(self, expected_days: int) -> None:
        if len(self.days) != expected_days:
            raise ItineraryDurationError(
                "The generated itinerary does not match the trip duration."
            )


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
