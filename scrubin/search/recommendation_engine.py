'''Recommendation engine – ranks candidate experiments deterministically.'''
from __future__ import annotations

import hashlib
import json
import math
from typing import List, Tuple, Dict, Any

from .search_models import SearchCandidate, SearchRecommendation, SearchHistory, SearchRequest
from .similarity_engine import SimilarityEngine


class RecommendationEngine:
    """Ranks candidates based on deterministic criteria (exploratory distance)."""

    @staticmethod
    def _candidate_score(candidate: SearchCandidate, history: Tuple[SearchHistory, ...]) -> float:
        """Compute a deterministic score for a candidate.

        Higher score = more exploratory (larger minimum distance to any existing history entry).
        If no history, return infinity to prioritize exploration.
        """
        if not history:
            return float('inf')
        cand_params = candidate.parameters
        min_dist = float('inf')
        for entry in history:
            hist_params = dict(entry.parameters)
            # Compute distance: numeric Euclidean for numeric values, +1 for categorical mismatches
            dist = 0.0
            for key in cand_params.keys() & hist_params.keys():
                v1 = cand_params[key]
                v2 = hist_params[key]
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    diff = float(v1) - float(v2)
                    dist += diff * diff
                else:
                    if v1 != v2:
                        dist += 1.0
            # Extra keys present in only one side count as full mismatch (categorical)
            extra_keys = cand_params.keys() ^ hist_params.keys()
            dist += float(len(extra_keys))
            euclidean = math.sqrt(dist)
            if euclidean < min_dist:
                min_dist = euclidean
        return min_dist

    @staticmethod
    def _hash_candidate(candidate: SearchCandidate, request: SearchRequest) -> str:
        data = {
            "objective": request.objective,
            "seed": request.seed,
            "parameters": {k: v for k, v in sorted(candidate.parameters.items())},
        }
        json_str = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(json_str).hexdigest()

    @staticmethod
    def rank_candidates(
        candidates: List[SearchCandidate],
        history_engine: "HistoryEngine",
        request: SearchRequest,
    ) -> List[SearchRecommendation]:
        """Rank candidates deterministically and produce recommendations with explanations and hashes."""
        history = history_engine.get_all()
        scored = []
        for cand in candidates:
            score = RecommendationEngine._candidate_score(cand, history)
            hashed = RecommendationEngine._hash_candidate(cand, request)
            explanation = (
                f"Exploratory candidate with min distance {score:.3f}" if score != float('inf') else "Exploratory candidate (no prior history)"
            )
            scored.append((score, hashed, cand, explanation))
        # Sort by descending score (larger distance first), then by hash for deterministic tie‑break
        scored.sort(key=lambda x: (-x[0], x[1]))
        recommendations = [
            SearchRecommendation(candidate=cand, explanation=explanation, recommendation_hash=hashed)
            for _, hashed, cand, explanation in scored
        ]
        return recommendations
