'''Optimization API routes – read‑only endpoints under /dashboard/optimization/*.'''
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from scrubin.server.dependency_provider import get_optimization_manager
from .optimization_models import OptimizationRequest
from .optimization_manager import OptimizationManager

router = APIRouter()

def _build_request(experiment_id: str, objectives: str, seed: int, ranking_method: str = "pareto") -> OptimizationRequest:
    obj_tuple = tuple(o.strip() for o in objectives.split(",") if o.strip())
    metadata = {"ranking_method": ranking_method} if ranking_method else {}
    return OptimizationRequest(
        experiment_id=experiment_id,
        objectives=obj_tuple,
        seed=seed,
        metadata=metadata,
    )

def _point_to_dict(point):
    return {
        "experiment_id": point.experiment_id,
        "parameters": {k: v for k, v in point.parameters},
        "scores": {s.name: s.score for s in point.scores},
    }

@router.get("/optimization/report")
def get_report(
    experiment_id: str = Query(..., description="Experiment identifier"),
    objectives: str = Query(..., description="Comma‑separated list of objective names"),
    seed: int = Query(..., description="Deterministic seed"),
    ranking_method: str = Query("pareto", description="Ranking method (pareto, weighted_sum, lexicographic)"),
    manager: OptimizationManager = Depends(get_optimization_manager),
):
    request = _build_request(experiment_id, objectives, seed, ranking_method)
    result = manager.optimize(request)
    report = {
        "request": {
            "experiment_id": result.request.experiment_id,
            "objectives": list(result.request.objectives),
            "seed": result.request.seed,
            "metadata": result.request.metadata,
        },
        "overall_hash": result.overall_hash,
        "metadata": {
            "created_at": result.metadata.created_at,
            "version": result.metadata.version,
        },
        "pareto_front": [_point_to_dict(p) for p in result.pareto_front.points],
        "rankings": [{"experiment_id": exp_id, "rank": rank} for exp_id, rank in result.rankings],
    }
    return jsonable_encoder(report)

@router.get("/optimization/front")
def get_front(
    experiment_id: str = Query(...),
    objectives: str = Query(...),
    seed: int = Query(...),
    ranking_method: str = Query("pareto"),
    manager: OptimizationManager = Depends(get_optimization_manager),
):
    request = _build_request(experiment_id, objectives, seed, ranking_method)
    result = manager.optimize(request)
    front = [_point_to_dict(p) for p in result.pareto_front.points]
    return jsonable_encoder(front)

@router.get("/optimization/rankings")
def get_rankings(
    experiment_id: str = Query(...),
    objectives: str = Query(...),
    seed: int = Query(...),
    ranking_method: str = Query("pareto"),
    manager: OptimizationManager = Depends(get_optimization_manager),
):
    request = _build_request(experiment_id, objectives, seed, ranking_method)
    result = manager.optimize(request)
    return jsonable_encoder([{"experiment_id": exp_id, "rank": rank} for exp_id, rank in result.rankings])

@router.get("/optimization/summary")
def get_summary(
    experiment_id: str = Query(...),
    objectives: str = Query(...),
    seed: int = Query(...),
    ranking_method: str = Query("pareto"),
    manager: OptimizationManager = Depends(get_optimization_manager),
):
    request = _build_request(experiment_id, objectives, seed, ranking_method)
    result = manager.optimize(request)
    total_candidates = len(manager.get_history())
    pareto_size = len(result.pareto_front.points)
    dominated = total_candidates - pareto_size
    summary = {
        "total_candidates": total_candidates,
        "pareto_size": pareto_size,
        "dominated_solutions": dominated,
        "ranking_method": ranking_method,
        "optimization_hash": result.overall_hash,
    }
    return jsonable_encoder(summary)
