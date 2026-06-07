'''Adaptive search engine – orchestrates deterministic recommendation of next experiments.'''
from __future__ import annotations

import hashlib
import datetime
import json

from typing import Tuple, Any

from .search_models import SearchRequest, SearchResult, SearchRecommendation, SearchHistory
from .experiment_history import HistoryEngine
from .acquisition_engine import AcquisitionEngine
from .recommendation_engine import RecommendationEngine

# Reuse ExperimentPlanner to generate ExperimentDefinition objects
from scrubin.planner.experiment_planner import ExperimentPlanner
from scrubin.experiments.experiment_models import ExperimentDefinition


class AdaptiveSearchEngine:
    """Main engine that produces deterministic experiment recommendations based on history."""

    def __init__(self) -> None:
        self.history_engine = HistoryEngine()
        self.experiment_planner = ExperimentPlanner(kernel=None)  # Kernel unused for planning only

    # ---------------------------------------------------------------------
    # History handling
    # ---------------------------------------------------------------------
    def add_history(self, entry: SearchHistory) -> None:
        """Add a completed experiment entry to the internal history (immutable update)."""
        self.history_engine = self.history_engine.add(entry)

    def get_history(self) -> Tuple[SearchHistory, ...]:
        return self.history_engine.get_all()

    # ---------------------------------------------------------------------
    # Search operation
    # ---------------------------------------------------------------------
    def search(self, request: SearchRequest) -> SearchResult:
        """Generate deterministic recommendations for the given request.

        Returns a SearchResult containing ranked recommendations and a deterministic overall hash.
        """
        # 1. Generate candidate parameter sets via acquisition strategies
        candidates = AcquisitionEngine.grid_refinement(request.seed, self.history_engine)
        # 2. Rank candidates deterministically
        recommendations = RecommendationEngine.rank_candidates(candidates, self.history_engine, request)
        # 3. Compute overall recommendation hash – deterministic over sorted recommendation hashes
        combined_hash_input = {
            "objective": request.objective,
            "seed": request.seed,
            "recommendation_hashes": [rec.recommendation_hash for rec in recommendations],
        }
        hash_bytes = json.dumps(combined_hash_input, sort_keys=True).encode()
        overall_hash = hashlib.sha256(hash_bytes).hexdigest()
        # 4. Build ExperimentDefinition for the top recommendation (if any)
        if recommendations:
            top_params = recommendations[0].candidate.parameters
            # Build a deterministic experiment definition using the existing planner infrastructure
            name_hash = hashlib.sha256(f"{request.objective}{request.seed}{sorted(top_params.items())}".encode()).hexdigest()[:8]
            exp_name = f"search_{name_hash}"
            tick_count = request.metadata.get("tick_count", 100)
            definition = ExperimentDefinition(
                name=exp_name,
                seeds=(request.seed,),
                tick_count=tick_count,
                parameters=top_params,
                metadata=request.metadata,
                initial_state={},
                config={},
            )
        else:
            definition = None
        return SearchResult(
            recommendations=tuple(recommendations),
            recommendation_hash=overall_hash,
            next_experiment=definition,
        )
