'''Objective engine – computes deterministic objective scores from completed experiment runs (Phase P.14).'''
from __future__ import annotations

from typing import Tuple, List, Dict, Any

from .optimization_models import OptimizationRequest, ObjectiveScore
from scrubin.search.search_models import SearchHistory


class ObjectiveEngine:
    """Evaluates each objective for a set of experiment histories deterministically."""

    @staticmethod
    def _parse_objective(name: str) -> Tuple[str, str]:
        """Return (direction, metric_key) extracted from an objective name.

        Supported prefixes are ``maximize_`` and ``minimize_``. If no prefix is present,
        the default direction is ``maximize`` and the entire string is taken as the metric key.
        """
        if name.startswith("maximize_"):
            return ("maximize", name[len("maximize_"):])
        if name.startswith("minimize_"):
            return ("minimize", name[len("minimize_"):])
        # Default – treat as maximize with the whole name as metric
        return ("maximize", name)

    @staticmethod
    def evaluate(request: OptimizationRequest, histories: Tuple[SearchHistory, ...]) -> List[Tuple[SearchHistory, Tuple[float, ...]]]:
        """Compute all objective scores for each history entry.

        Returns a list of ``(history, scores)`` where ``scores`` is a tuple ordered
        exactly as ``request.objectives``.
        """
        result: List[Tuple[SearchHistory, Tuple[float, ...]]] = []
        for entry in histories:
            scores: List[float] = []
            for obj_name in request.objectives:
                direction, metric_key = ObjectiveEngine._parse_objective(obj_name)
                raw = entry.metrics.get(metric_key, 0)
                try:
                    value = float(raw)
                except Exception:
                    value = 0.0
                scores.append(value)
            result.append((entry, tuple(scores)))
        return result
