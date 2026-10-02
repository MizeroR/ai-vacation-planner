import base64
import json
import re
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from app.config import settings
from app.schemas.media import ImageAnalysisResponse


class ImageAnalysisError(Exception):
    """Raised when image analysis fails."""


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()

    if not text:
        raise ValueError("The image analysis returned no content.")

    if text.startswith("```"):
        text = text.strip("`")
        text = re.sub(r"^json\s*", "", text, flags=re.IGNORECASE)
        text = text.strip()

    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("The image analysis response was not valid JSON.")


def analyze_image(
    file_bytes: bytes | str | Path,
    *,
    request: str | None = None,
    destination: str | None = None,
) -> ImageAnalysisResponse:
    """Analyze a trip image using the Anthropic vision API."""

    if isinstance(file_bytes, (str, Path)):
        path = Path(file_bytes)
        if not path.exists():
            raise ImageAnalysisError("The image file could not be found.")
        file_bytes = path.read_bytes()

    if not file_bytes:
        raise ImageAnalysisError("No image data was provided.")

    media_type = "image/jpeg"
    if destination:
        prompt = (
            f"Analyze this travel photo in relation to {destination}. "
            "Provide a brief description, identify likely destination highlights, "
            "and list 2-5 short activity suggestions. "
            "Return valid JSON with keys: description, destination, activities."
        )
    else:
        prompt = (
            "Analyze this travel photo and infer the most likely destination vibe. "
            "Provide a brief description, identify the destination if it is clear, "
            "and list 2-5 short activity suggestions. "
            "Return valid JSON with keys: description, destination, activities."
        )

    if request and request.strip():
        prompt = f"{request.strip()}\n\n{prompt}"

    encoded = base64.b64encode(file_bytes).decode("utf-8")

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            temperature=settings.anthropic_temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                    ],
                }
            ],
        )
    except Exception as exc:
        raise ImageAnalysisError(
            "The image could not be analyzed by the vision model."
        ) from exc

    try:
        text = response.content[0].text
        payload = _extract_json_payload(text)
        description = payload.get("description") or "Image analyzed successfully."
        activities = payload.get("activities") or []
        destination_name = payload.get("destination") or destination
        return ImageAnalysisResponse(
            description=str(description),
            destination=(destination_name or None),
            activities=[str(item) for item in activities],
        )
    except Exception as exc:
        raise ImageAnalysisError(
            "The image analysis response could not be parsed."
        ) from exc
