'''Simple deterministic constraint handling for experiment planning.'''
from __future__ import annotations

from typing import Dict, Tuple, Any
from .planner_models import PlanningRequest, PlannerConstraint

class ConstraintEngine:
    """Apply planner constraints to a parameter grid.

    Currently implements a no‑op for most constraints, but respects ``max_runs`` 
    by returning the total combination count for downstream capping.
    """

    @staticmethod
    def apply(request: PlanningRequest, param_grid: Dict[str, Tuple[Any, ...]]) -> Tuple[Dict[str, Tuple[Any, ...]], int]:
        """Return (possibly modified) param_grid and total combo count.

        The function is deterministic. Future constraint types can be added here.
        """
        total = 1
        for values in param_grid.values():
            total *= len(values)
        # No further modification – constraints such as allowed_range are handled in ParameterPlanner.
        return param_grid, total
