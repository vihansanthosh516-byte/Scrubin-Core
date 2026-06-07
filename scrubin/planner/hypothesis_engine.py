'''Deterministic hypothesis generation from a PlanningRequest.'''
from __future__ import annotations

from typing import Tuple

from .planner_models import PlanningRequest, Hypothesis


class HypothesisEngine:
    """Generate a fixed set of hypotheses for a given objective."""
    _BASE_HYPOTHESES = (
        "MAP decreases with blood loss.",
        "Fluids improve recovery.",
        "Older patients recover more slowly.",
    )

    @staticmethod
    def generate(request: PlanningRequest) -> Tuple[Hypothesis, ...]:
        # Deterministic – always return the base list in the defined order.
        return tuple(Hypothesis(desc) for desc in HypothesisEngine._BASE_HYPOTHESES)