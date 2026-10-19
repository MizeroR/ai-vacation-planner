from pydantic import BaseModel, Field


class VoiceTripRequest(BaseModel):
    trip_id: int = Field(..., description="Trip to update or use as context")
    request: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional text instruction accompanying the voice input",
    )


class SpeechResponse(BaseModel):
    text: str
    language: str | None = None


class AudioResponse(BaseModel):
    media_type: str
    filename: str


class ImageAnalysisResponse(BaseModel):
    description: str
    destination: str | None = None
    activities: list[str] = Field(default_factory=list)


class MultimodalTripRequest(BaseModel):
    trip_id: int
    request: str | None = Field(default=None, max_length=2000)