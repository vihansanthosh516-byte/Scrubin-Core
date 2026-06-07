'''Dashboard API routes – read‑only inspection of simulation runs.'''
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from scrubin.server.dependency_provider import get_kernel
from scrubin.control_plane.p9_debug import DebugFacade

from .dashboard_models import (
    DashboardRunSummary,
    DashboardReplayFrame,
    DashboardMetricSeries,
    DashboardComparison,
    DashboardSnapshot,
)
from .replay_service import ReplayService
from .compare_service import CompareService
from .metrics_service import MetricsService
from .snapshot_service import SnapshotService

# Experiment manager dependency and models.
from scrubin.server.dependency_provider import get_experiment_manager
from scrubin.experiments.experiment_models import ExperimentDefinition, ExperimentRun

router = APIRouter()

def _load_artifact(kernel, run_id: str):
    facade = DebugFacade(kernel)
    return facade._get_artifact(run_id)

@router.get("/run/{run_id}", response_model=DashboardRunSummary)
def get_run_summary(run_id: str, kernel = Depends(get_kernel)):
    artifact = _load_artifact(kernel, run_id)
    meta = getattr(artifact, "metadata", {})
    return DashboardRunSummary(
        run_id=run_id,
        seed=meta.get("seed", 0),
        ticks=meta.get("ticks", 0),
        hash=meta.get("hash", ""),
    )

@router.get("/replay/{run_id}", response_model=List[DashboardReplayFrame])
def get_replay(run_id: str, kernel = Depends(get_kernel)):
    service = ReplayService(kernel)
    return service.get_frames(run_id)

@router.get("/replay/{run_id}/{tick}", response_model=DashboardReplayFrame)
def get_replay_tick(run_id: str, tick: int, kernel = Depends(get_kernel)):
    service = ReplayService(kernel)
    frames = service.get_frames(run_id, ticks=tick + 1)
    if 0 <= tick < len(frames):
        return frames[tick]
    raise HTTPException(status_code=404, detail="Tick not found")

@router.get("/compare/{run_a}/{run_b}", response_model=DashboardComparison)
def compare_runs(run_a: str, run_b: str, kernel = Depends(get_kernel)):
    service = CompareService(kernel)
    return service.compare(run_a, run_b)

@router.get("/metrics/{run_id}", response_model=List[DashboardMetricSeries])
def get_metrics(run_id: str, kernel = Depends(get_kernel)):
    service = MetricsService(kernel)
    return service.get_metrics(run_id)

@router.get("/snapshot/{run_id}", response_model=DashboardSnapshot)
def get_snapshot(run_id: str, kernel = Depends(get_kernel)):
    service = SnapshotService(kernel)
    return service.get_final_snapshot(run_id)
