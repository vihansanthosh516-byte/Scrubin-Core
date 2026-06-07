'''Ranking engine – deterministic ordering of Pareto points (Phase P.14).'''
from __future__ import annotations

from typing import List, Tuple

from .optimization_models import ParetoPoint, OptimizationRequest
from .pareto_engine import ParetoEngine


class RankingEngine:
    """Provides deterministic ranking of Pareto points based on multiple strategies."""

    @staticmethod
    def _parse_directions(request: OptimizationRequest) -> List[str]:
        """Parse direction (minimize/maximize) from request.objectives."""
        directions: List[str] = []
        for name in request.objectives:
            if name.startswith("maximize_"):
                directions.append("maximize")
            elif name.startswith("minimize_"):
                directions.append("minimize")
            else:
                directions.append("maximize")
        return directions

    @staticmethod
    def rank(points: List[ParetoPoint], request: OptimizationRequest, method: str = "pareto", weights: Tuple[float, ...] = None) -> List[Tuple[ParetoPoint, int]]:
        """Rank points deterministically according to ``method``.

        Supported methods: ``"pareto"`` – assign Pareto layer ranks;
        ``"weighted_sum"`` – rank by weighted sum (lower is better after direction handling);
        ``"lexicographic"`` – rank by lexicographic order of transformed scores.
        ``weights`` is used only for ``weighted_sum``; if omitted, equal weighting is applied.
        Returns a list of ``(point, rank)`` where ``rank`` is 1‑based.
        """
        directions = RankingEngine._parse_directions(request)
        if method == "pareto":
            return ParetoEngine.rank_by_layers(points, directions)
        # Transform scores according to direction for the other methods
        transformed: List[Tuple[ParetoPoint, Tuple[float, ...]]] = []
        for pt in points:
            vals: List[float] = []
            for score, dir in zip(pt.scores, directions):
                v = score.score
                if dir == "maximize":
                    vals.append(-v)
                else:
                    vals.append(v)
            transformed.append((pt, tuple(vals)))
        if method == "weighted_sum":
            if weights is None:
                weights = tuple(1.0 for _ in request.objectives)
            else:
                weights = tuple(weights)
            sums: List[Tuple[float, ParetoPoint]] = []
            for pt, vals in transformed:
                s = sum(w * v for w, v in zip(weights, vals))
                sums.append((s, pt))
            sums.sort(key=lambda x: (x[0], x[1].experiment_id))
            rankings: List[Tuple[ParetoPoint, int]] = []
            for idx, (_, pt) in enumerate(sums, start=1):
                rankings.append((pt, idx))
            return rankings
        if method == "lexicographic":
            transformed.sort(key=lambda x: (x[1], x[0].experiment_id))
            rankings = [(pt, idx) for idx, (pt, _) in enumerate(transformed, start=1)]
            return rankings
        raise ValueError(f"Unsupported ranking method: {method}")
