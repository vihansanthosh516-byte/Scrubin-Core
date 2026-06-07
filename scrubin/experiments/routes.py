'''Experiment API routes – read‑only inspection of deterministic experiment runs.'''
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from scrubin.server.dependency_provider import get_experiment_manager

router = APIRouter()

@router.get("/experiment/{exp_id}")
def get_experiment(exp_id: str, manager = Depends(get_experiment_manager)):
    definition = manager.get_definition(exp_id)
    return {
        "name": definition.name,
        "seeds": list(definition.seeds),
        "tick_count": definition.tick_count,
        "parameters": {k: list(v) for k, v in definition.parameters.items()},
        "metadata": definition.metadata,
        "initial_state": definition.initial_state,
        "config": definition.config,
    }

@router.get("/experiment/{exp_id}/runs")
def get_experiment_runs(exp_id: str, manager = Depends(get_experiment_manager)):
    runs = manager.get_runs(exp_id)
    result = []
    for run in runs:
        result.append({
            "run_id": run.run_id,
            "seed": run.seed,
            "status": run.status,
            "params": {k: v for k, v in run.params},
        })
    return result

@router.get("/experiment/{exp_id}/summary")
def get_experiment_summary(exp_id: str, manager = Depends(get_experiment_manager)):
    return manager.summarize(exp_id)

@router.get("/experiment/{exp_id}/metrics")
def get_experiment_metrics(exp_id: str, manager = Depends(get_experiment_manager)):
    summary = manager.summarize(exp_id)
    return [
        {"name": "total_runs", "values": [summary["total_runs"]]},
        {"name": "completed_runs", "values": [summary["completed_runs"]]},
        {"name": "failed_runs", "values": [summary["failed_runs"]]},
        {"name": "mean_ticks", "values": [summary["mean_ticks"]]},
    ]
