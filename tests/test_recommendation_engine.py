from scrubin.search.recommendation_engine import RecommendationEngine
from scrubin.search.search_models import SearchCandidate, SearchRequest, SearchHistory


def test_ranking_deterministic_order():
    request = SearchRequest(objective="obj", seed=42)
    cand1 = SearchCandidate(parameters={"a": 1})
    cand2 = SearchCandidate(parameters={"a": 2})
    candidates = [cand1, cand2]
    from scrubin.search.experiment_history import HistoryEngine
    history_engine = HistoryEngine()
    recommendations = RecommendationEngine.rank_candidates(candidates, history_engine, request)
    hashes = [rec.recommendation_hash for rec in recommendations]
    assert hashes == sorted(hashes)
