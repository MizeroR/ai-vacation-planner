import json
from pathlib import Path

from app.schemas.itinerary import ItineraryGenerateAI


DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluations"
    / "datasets"
    / "itinerary_goldens.json"
)


def test_itinerary_golden_dataset_has_unique_complete_cases():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    assert dataset["version"] == 1
    assert len(dataset["cases"]) >= 4
    assert len({case["id"] for case in dataset["cases"]}) == len(dataset["cases"])

    for case in dataset["cases"]:
        assert case["trip"]["destination"]
        assert case["trip"]["days"] >= 1
        assert case["trip"]["budget"] > 0
        assert case["trip"]["trip_style"]
        assert case["request"]
        assert len(case["expected_requirements"]) >= 3
        ItineraryGenerateAI.model_validate(
            {
                "trip_id": 1,
                "request": case["request"],
            }
        )
