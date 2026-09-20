from app.services.knowledge import KnowledgeBase
from app.services import planner
from app.tools import travel


def test_knowledge_base_does_not_load_model_during_initialization(tmp_path):
    knowledge_base = KnowledgeBase(storage_dir=str(tmp_path))

    assert knowledge_base._model is None


def test_knowledge_query_bounds_top_k(monkeypatch, tmp_path):
    knowledge_base = KnowledgeBase(storage_dir=str(tmp_path))

    calls = {}

    class FakeModel:
        def encode(self, values, show_progress_bar=False):
            calls["values"] = values
            return [[1.0, 0.0]]

    knowledge_base._model = FakeModel()
    knowledge_base._embeddings = __import__("numpy").array(
        [[1.0, 0.0]],
        dtype="float32",
    )

    class FakeIndex:
        def kneighbors(self, query_embedding, n_neighbors):
            calls["n_neighbors"] = n_neighbors
            return [[0.0]], [[0]]

    knowledge_base._nn = FakeIndex()
    knowledge_base._metadata = [{"text": "Paris tip"}]

    result = knowledge_base.query("Paris", top_k=100)

    assert calls["n_neighbors"] == 1
    assert result[0]["text"] == "Paris tip"


def test_knowledge_tool_returns_unavailable_on_failure(monkeypatch):
    class FailingKnowledgeBase:
        def query(self, query, top_k):
            raise RuntimeError("embedding provider failed")

    monkeypatch.setattr(travel, "kb", FailingKnowledgeBase())

    result = travel.search_travel_knowledge.invoke(
        {"query": "Paris", "top_k": 5}
    )

    assert result == [
        {
            "status": "unavailable",
            "reason": "Travel knowledge is temporarily unavailable.",
        }
    ]


def test_planner_hides_internal_exception(monkeypatch):
    def failing_graph(model):
        raise RuntimeError("internal provider details")

    monkeypatch.setattr(planner, "create_planner_graph", failing_graph)
    monkeypatch.setattr(planner, "get_chat_model", lambda: object())

    try:
        planner.generate_planned_itinerary(
            destination="Paris",
            days=1,
            budget=500,
            trip_style="budget",
        )
    except planner.PlannerUnavailable as exc:
        assert str(exc) == "The itinerary planner is temporarily unavailable."
        assert "internal provider details" not in str(exc)
    else:
        raise AssertionError("Expected PlannerUnavailable")