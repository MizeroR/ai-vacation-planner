import pytest

pytest.importorskip("deepeval")

from deepeval.models import AnthropicModel
from deepeval.metrics.g_eval.schema import ReasonScore
from deepeval.models.utils import EvaluationCost

from evaluations.judge import JsonSchemaAnthropicModel
from evaluations.run_deepeval import _read_goldens, _select_goldens


def _judge():
    judge = object.__new__(JsonSchemaAnthropicModel)
    judge.name = "test-anthropic-model"
    return judge


def test_judge_validates_complete_json_score(monkeypatch):
    prompts = []

    def fake_generate(self, prompt, schema=None, audio=None):
        prompts.append(prompt)
        return '{"score": 8, "reason": "Good itinerary."}', 0.01

    monkeypatch.setattr(AnthropicModel, "generate", fake_generate)

    result, cost = _judge().generate("Evaluate this itinerary.", schema=ReasonScore)

    assert result.score == 8
    assert result.reason == "Good itinerary."
    assert cost == 0.01
    assert '"score"' in prompts[0]
    assert '"reason"' in prompts[0]


def test_judge_retries_once_when_score_is_missing(monkeypatch):
    prompts = iter(
        [
            '{"reason": "It satisfies the preferences."}',
            '{"score": 9, "reason": "It satisfies the preferences."}',
        ]
    )
    observed_prompts = []

    def fake_generate(self, prompt, schema=None, audio=None):
        observed_prompts.append(prompt)
        return next(prompts), EvaluationCost(0.02, 10, 4)

    monkeypatch.setattr(AnthropicModel, "generate", fake_generate)

    result, cost = _judge().generate("Evaluate this itinerary.", schema=ReasonScore)

    assert result.score == 9
    assert cost == 0.04
    assert cost.input_tokens == 20
    assert cost.output_tokens == 8
    assert len(observed_prompts) == 2
    assert "previous response was missing or invalid" in observed_prompts[1]


def test_judge_fails_clearly_if_corrected_response_is_invalid(monkeypatch):
    monkeypatch.setattr(
        AnthropicModel,
        "generate",
        lambda self, prompt, schema=None, audio=None: (
            '{"reason": "Score omitted."}',
            0.01,
        ),
    )

    with pytest.raises(ValueError, match="after one correction attempt"):
        _judge().generate("Evaluate this itinerary.", schema=ReasonScore)


def test_judge_disables_unsupported_log_probability_path():
    assert _judge().supports_log_probs() is False


def test_case_id_selects_exactly_one_golden_case():
    dataset = _read_goldens()

    selected = _select_goldens(dataset.goldens, "paris-budget-museums")

    assert [golden.id for golden in selected] == ["paris-budget-museums"]


def test_unknown_case_id_reports_valid_choices():
    dataset = _read_goldens()

    with pytest.raises(ValueError, match="Unknown evaluation case"):
        _select_goldens(dataset.goldens, "unknown-case")
