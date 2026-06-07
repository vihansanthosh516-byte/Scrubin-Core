from scrubin.search.adaptive_search import AdaptiveSearchEngine
from scrubin.search.search_models import SearchRequest, SearchHistory


def test_adaptive_search_generates_recommendation_and_experiment():
    engine = AdaptiveSearchEngine()
    request = SearchRequest(objective="test_obj", seed=123)
    result = engine.search(request)
    assert len(result.recommendations) > 0
    assert result.next_experiment is not None
    assert result.next_experiment.name.startswith("search_")
    # Add history entry and re-search
    entry = SearchHistory(
        experiment_id=result.next_experiment.name,
        run_id="run1",
        replay_hash="hash",
        parameters=tuple(sorted(result.next_experiment.parameters.items())),
        metrics={},
        timestamp="2022-01-01",
        metadata={},
    )
    engine.add_history(entry)
    result2 = engine.search(request)
    assert result2.next_experiment is not None
    assert result2.next_experiment.name != result.next_experiment.name
