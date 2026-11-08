import argparse
import json
from pathlib import Path

from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from app.config import settings
from app.schemas.itinerary import ItineraryPlan
from app.services.planner import generate_planned_itinerary
from evaluations.judge import JsonSchemaAnthropicModel


DATASET_PATH = Path(__file__).parent / "datasets" / "itinerary_goldens.json"


def _read_goldens() -> EvaluationDataset:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    goldens = []

    for case in payload["cases"]:
        input_text = json.dumps(
            {
                "trip": case["trip"],
                "request": case["request"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        expected_output = "\n".join(
            f"- {requirement}"
            for requirement in case["expected_requirements"]
        )
        goldens.append(
            Golden(
                id=case["id"],
                input=input_text,
                expected_output=expected_output,
                additional_metadata={
                    "trip": case["trip"],
                    "request": case["request"],
                },
            )
        )

    return EvaluationDataset(goldens=goldens)


def _select_goldens(
    goldens: list[Golden],
    case_id: str | None,
) -> list[Golden]:
    if case_id is None:
        return goldens

    selected = [golden for golden in goldens if golden.id == case_id]
    if not selected:
        valid_ids = ", ".join(golden.id for golden in goldens)
        raise ValueError(
            f"Unknown evaluation case '{case_id}'. Choose one of: {valid_ids}"
        )
    return selected


def run_evaluation(case_id: str | None = None) -> bool:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required to run AI evaluations.")

    dataset = _read_goldens()
    goldens = _select_goldens(dataset.goldens, case_id)

    judge = JsonSchemaAnthropicModel(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
    )
    quality_metric = GEval(
        name="Itinerary quality",
        criteria=(
            "Assess whether the generated itinerary satisfies the explicit trip "
            "requirements and expected output. Check destination, duration, "
            "budget and travel style fit, requested preferences, realistic pacing, "
            "and whether activities are specific and useful. Do not require "
            "unsupported exact prices, weather, or opening-hour claims."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        model=judge,
        threshold=0.7,
        async_mode=False,
    )

    all_passed = True
    for golden in goldens:
        metadata = golden.additional_metadata
        trip = metadata["trip"]
        itinerary_days = generate_planned_itinerary(
            destination=trip["destination"],
            days=trip["days"],
            budget=trip["budget"],
            trip_style=trip["trip_style"],
            request=metadata["request"],
        )
        plan = ItineraryPlan.model_validate({"days": itinerary_days})
        plan.validate_duration(trip["days"])

        test_case = LLMTestCase(
            input=golden.input,
            actual_output=json.dumps(
                [day.model_dump() for day in plan.days],
                ensure_ascii=False,
            ),
            expected_output=golden.expected_output,
        )
        quality_metric.measure(test_case)
        passed = quality_metric.is_successful()
        all_passed = all_passed and passed
        print(
            f"{golden.id}: {'PASS' if passed else 'FAIL'} "
            f"(score={quality_metric.score:.2f}, "
            f"threshold={quality_metric.threshold:.2f})"
        )
        if quality_metric.reason:
            print(f"  reason: {quality_metric.reason}")

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run itinerary DeepEval cases.")
    parser.add_argument(
        "--case-id",
        help="Run only one golden case as a live smoke evaluation.",
    )
    arguments = parser.parse_args()
    raise SystemExit(0 if run_evaluation(arguments.case_id) else 1)
