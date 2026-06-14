'''Optimization manager – orchestrates deterministic multi‑objective evaluation (Phase P.14).'''
from __future__ import annotations

import hashlib
import json
import datetime
from typing import Tuple, List, Dict, Any

from .optimization_models import (
    OptimizationRequest,
    OptimizationResult,
    OptimizationMetadata,
    ParetoFront,
    ParetoPoint,
    ObjectiveScore,
)
from .objective_engine import ObjectiveEngine
from .pareto_engine import ParetoEngine
from .ranking_engine import RankingEngine

from scrubin.search.experiment_history import HistoryEngine
from scrubin.search.search_models import SearchHistory


class OptimizationManager:
    """Deterministic manager for multi‑objective optimization over experiment history."""

    def __init__(self) -> None:
        self.history_engine = HistoryEngine()

    # History handling
    def add_history(self, entry: SearchHistory) -> None:
        """Add a completed experiment entry to the internal immutable history store."""
        self.history_engine = self.history_engine.add(entry)

    def get_history(self) -> Tuple[SearchHistory, ...]:
        return self.history_engine.get_all()

    # Core optimization workflow
    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        """Execute deterministic multi‑objective optimization and return a result object."""
        # 1. Gather histories (deterministically ordered)
        histories = self.get_history()

        # 2. Evaluate objectives for each history entry
        evaluated = ObjectiveEngine.evaluate(request, histories)  # List[(SearchHistory, Tuple[float, ...])]

        # 3. Build Pareto points
        points: List[ParetoPoint] = []
        for entry, scores in evaluated:
            obj_scores = tuple(
                ObjectiveScore(name=obj, score=score) for obj, score in zip(request.objectives, scores)
            )
            point = ParetoPoint(
                experiment_id=entry.experiment_id,
                parameters=entry.parameters,
                scores=obj_scores,
            )
            points.append(point)

        # 4. Determine directions for Pareto comparison
        directions = RankingEngine._parse_directions(request)

        # 5. Compute Pareto front
        front = ParetoEngine.compute_front(points, directions)

        # 6. Rank points – default can be overridden via request.metadata['ranking_method']
        ranking_method = request.metadata.get("ranking_method", "pareto")
        ranked = RankingEngine.rank(points, request, method=ranking_method)

        # Convert rankings to tuple of (experiment_id, rank)
        rankings_tuple = tuple((pt.experiment_id, rank) for pt, rank in ranked)

        # 7. Compute deterministic hash
        hash_input: Dict[str, Any] = {
            "request": {
                "experiment_id": request.experiment_id,
                "objectives": list(request.objectives),
                "constraints": list(request.constraints),
                "seed": request.seed,
                "metadata": request.metadata,
            },
            "points": [
                {
                    "experiment_id": p.experiment_id,
                    "scores": [s.score for s in p.scores],
                }
                for p in sorted(points, key=lambda x: x.experiment_id)
            ],
            "ranking_method": ranking_method,
        }
        hash_bytes = json.dumps(hash_input, sort_keys=True).encode()
        overall_hash = hashlib.sha256(hash_bytes).hexdigest()

        # 8. Result metadata
        metadata = OptimizationMetadata(created_at=datetime.datetime.now(datetime.UTC).isoformat())

        # 9. Assemble result
        result = OptimizationResult(
            request=request,
            overall_hash=overall_hash,
            pareto_front=front,
            rankings=rankings_tuple,
            metadata=metadata,
        )
        return result
