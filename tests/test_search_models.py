import pytest
from dataclasses import FrozenInstanceError

from scrubin.search.search_models import (
    SearchRequest,
    SearchCandidate,
    SearchRecommendation,
    SearchHistory,
    SearchResult,
)


def test_search_models_are_frozen():
    req = SearchRequest(objective="obj", seed=1)
    with pytest.raises(FrozenInstanceError):
        req.objective = "new"

    cand = SearchCandidate(parameters={"a": 1})
    with pytest.raises(FrozenInstanceError):
        cand.parameters["a"] = 2

    rec = SearchRecommendation(candidate=cand, explanation="test", recommendation_hash="hash")
    with pytest.raises(FrozenInstanceError):
        rec.explanation = "changed"

    hist = SearchHistory(
        experiment_id="exp1",
        run_id="run1",
        replay_hash="hash",
        parameters=(("a", 1),),
        metrics={},
        timestamp="2022-01-01",
        metadata={},
    )
    with pytest.raises(FrozenInstanceError):
        hist.experiment_id = "exp2"

    result = SearchResult(recommendations=(), recommendation_hash="hash", next_experiment=None)
    with pytest.raises(FrozenInstanceError):
        result.recommendation_hash = "new"
