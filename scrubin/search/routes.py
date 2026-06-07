'''Search API routes – read‑only endpoints under /dashboard/search/*.'''
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from scrubin.server.dependency_provider import get_adaptive_search_engine
from .search_models import SearchRequest, SearchResult, SearchRecommendation, SearchHistory

router = APIRouter()

@router.get("/search/history")
def get_history(engine = Depends(get_adaptive_search_engine)):
    history = engine.get_history()
    result = []
    for entry in history:
        result.append({
            "experiment_id": entry.experiment_id,
            "run_id": entry.run_id,
            "replay_hash": entry.replay_hash,
            "parameters": {k: v for k, v in entry.parameters},
            "metrics": entry.metrics,
            "timestamp": entry.timestamp,
            "metadata": entry.metadata,
        })
    return jsonable_encoder(result)

@router.get("/search/recommendations")
def get_recommendations(
    objective: str = Query(..., description="Research objective"),
    seed: int = Query(..., description="Deterministic seed"),
    engine = Depends(get_adaptive_search_engine),
):
    request = SearchRequest(objective=objective, seed=seed)
    result: SearchResult = engine.search(request)
    recs = []
    for rec in result.recommendations:
        recs.append({
            "parameters": rec.candidate.parameters,
            "explanation": rec.explanation,
            "hash": rec.recommendation_hash,
        })
    return jsonable_encoder({
        "recommendations": recs,
        "overall_hash": result.recommendation_hash,
    })

@router.get("/search/summary")
def get_summary(engine = Depends(get_adaptive_search_engine)):
    from .search_summary import generate_summary
    from scrubin.planner.parameter_planner import ParameterPlanner
    default_grid = ParameterPlanner._DEFAULT_RANGES
    summary = generate_summary(engine.history_engine, total_recommendations=0, default_grid=default_grid)
    return jsonable_encoder(summary.to_dict())

@router.get("/search/frontier")
def get_frontier(engine = Depends(get_adaptive_search_engine)):
    return {"detail": "Frontier endpoint not implemented in this stub"}
