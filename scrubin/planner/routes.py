'''Planner API routes – read‑only endpoints under /dashboard/planner/*'''
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from scrubin.server.dependency_provider import get_planner_engine
from .experiment_planner import ExperimentPlanner
from .planner_models import PlanningRequest

router = APIRouter()

def _make_request(objective: str, seed: int, max_runs: int = 0) -> PlanningRequest:
    # Minimal request – other fields left empty/default.
    return PlanningRequest(objective=objective, seed=seed, max_runs=max_runs)

@router.get("/planner/plan")
def get_plan(
    objective: str = Query(..., description="Research objective"),
    seed: int = Query(..., description="Deterministic seed"),
    max_runs: int = Query(0, description="Maximum runs limit (optional)"),
    engine: ExperimentPlanner = Depends(get_planner_engine),
):
    request = _make_request(objective, seed, max_runs)
    result = engine.plan(request)
    return jsonable_encoder({
        "experiment_definition": {
            "name": result.experiment_definition.name,
            "seeds": list(result.experiment_definition.seeds),
            "tick_count": result.experiment_definition.tick_count,
            "parameters": {k: list(v) for k, v in result.experiment_definition.parameters.items()},
            "metadata": result.experiment_definition.metadata,
            "initial_state": result.experiment_definition.initial_state,
            "config": result.experiment_definition.config,
        },
        "planning_hash": result.planning_hash,
    })

@router.get("/planner/hypotheses")
def get_hypotheses(
    objective: str = Query(...),
    seed: int = Query(...),
    max_runs: int = Query(0),
    engine: ExperimentPlanner = Depends(get_planner_engine),
):
    request = _make_request(objective, seed, max_runs)
    result = engine.plan(request)
    return jsonable_encoder([h.description for h in result.hypotheses])

@router.get("/planner/summary")
def get_summary(
    objective: str = Query(...),
    seed: int = Query(...),
    max_runs: int = Query(0),
    engine: ExperimentPlanner = Depends(get_planner_engine),
):
    request = _make_request(objective, seed, max_runs)
    result = engine.plan(request)
    summary = {
        "planning_hash": result.planning_hash,
        "estimated_run_count": result.estimated_run_count,
        "parameter_summary": result.parameter_summary,
        "hypotheses_count": len(result.hypotheses),
    }
    return jsonable_encoder(summary)
