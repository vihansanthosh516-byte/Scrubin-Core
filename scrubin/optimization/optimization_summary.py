'''Summary utilities for deterministic optimization (Phase P.14).'''
from __future__ import annotations

from typing import Dict, Any

from .optimization_manager import OptimizationManager
from .optimization_models import OptimizationRequest, OptimizationResult


def generate_summary(manager: OptimizationManager, request: OptimizationRequest, result: OptimizationResult) -> Dict[str, Any]:
    """Return a deterministic summary dictionary for the given optimization result."""
    total = len(manager.get_history())
    pareto = len(result.pareto_front.points)
    dominated = total - pareto
    summary = {
        "total_candidates": total,
        "pareto_size": pareto,
        "dominated_solutions": dominated,
        "ranking_method": request.metadata.get("ranking_method", "pareto"),
        "optimization_hash": result.overall_hash,
    }
    return summary
