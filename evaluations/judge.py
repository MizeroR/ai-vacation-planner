import json
from typing import Any

from pydantic import BaseModel, ValidationError

from deepeval.errors import DeepEvalError
from deepeval.models import AnthropicModel
from deepeval.models.llms.utils import trim_and_load_json
from deepeval.models.utils import EvaluationCost


def _combined_cost(costs: list[float | None]) -> float | None:
    known_costs = [cost for cost in costs if cost is not None]
    if not known_costs:
        return None

    total = sum(float(cost) for cost in known_costs)
    if not any(hasattr(cost, "input_tokens") for cost in known_costs):
        return total

    input_tokens = sum(
        getattr(cost, "input_tokens", 0) or 0 for cost in known_costs
    )
    output_tokens = sum(
        getattr(cost, "output_tokens", 0) or 0 for cost in known_costs
    )
    cost_is_known = any(
        getattr(cost, "value", cost) is not None for cost in known_costs
    )
    return EvaluationCost(
        total if cost_is_known else None,
        input_tokens,
        output_tokens,
    )


class JsonSchemaAnthropicModel(AnthropicModel):
    def supports_log_probs(self) -> bool:
        return False

    def generate(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
        audio: list[Any] | None = None,
    ):
        if schema is None:
            return super().generate(prompt, audio=audio)

        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        schema_prompt = (
            f"{prompt}\n\n"
            "Return exactly one JSON object that conforms to this schema. "
            "Include every required field; do not omit a field:\n"
            f"{schema_json}"
        )
        costs: list[float | None] = []

        for attempt in range(2):
            if attempt:
                schema_prompt += (
                    "\nThe previous response was missing or invalid. "
                    "Re-evaluate and return a complete valid JSON object."
                )

            response_text, cost = super().generate(schema_prompt, audio=audio)
            costs.append(cost)
            try:
                parsed = trim_and_load_json(response_text)
                return schema.model_validate(parsed), _combined_cost(costs)
            except (DeepEvalError, ValidationError) as exc:
                if attempt:
                    raise ValueError(
                        f"{self.get_model_name()} did not return a valid "
                        f"{schema.__name__} after one correction attempt."
                    ) from exc

        raise RuntimeError("The evaluation judge exhausted its response attempts.")
