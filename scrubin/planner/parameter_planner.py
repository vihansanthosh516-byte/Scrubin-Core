'''Deterministic parameter grid generation for experiment planning.'''
from __future__ import annotations

from typing import Dict, Tuple, Any

from .planner_models import PlanningRequest


class ParameterPlanner:
    """Generate a default deterministic parameter grid, optionally respecting constraints."""
    _DEFAULT_RANGES: Dict[str, Tuple[Any, ...]] = {
        "blood_loss": (0.1, 0.2, 0.3),
        "fluids": (False, True),
        "age": (20, 50, 80),
    }

    @staticmethod
    def generate(request: PlanningRequest) -> Dict[str, Tuple[Any, ...]]:
        # Start with the defaults.
        param_grid: Dict[str, Tuple[Any, ...]] = dict(ParameterPlanner._DEFAULT_RANGES)
        # Apply any allowed_range constraints if present.
        for cons in request.constraints:
            if cons.type == "allowed_range":
                # Expect parameters as ((name, (v1, v2, ...)),)
                for name, values in cons.parameters:
                    param_grid[name] = tuple(values)
        # Return a deterministic mapping – keys order not relied upon downstream.
        return param_grid
