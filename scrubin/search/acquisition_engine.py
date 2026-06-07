'''Acquisition strategies for deterministic adaptive search.'''
from __future__ import annotations

from typing import List, Dict, Any
from itertools import product

from .search_models import SearchCandidate
from .experiment_history import HistoryEngine

# Reuse default parameter ranges from the existing planner for deterministic grounding
from scrubin.planner.parameter_planner import ParameterPlanner


class AcquisitionEngine:
    """Deterministic acquisition strategies to propose new parameter candidates."""

    @staticmethod
    def grid_refinement(seed: int, history: HistoryEngine) -> List[SearchCandidate]:
        """Propose a single candidate based on unseen default values.

        For each parameter, the set of observed values (from ``history``) is
        collected. The candidate uses the *first* unseen value for integer
        parameters and the *last* unseen value for floating‑point parameters.
        Boolean parameters have only two values, so the unseen value is the
        opposite of the observed one. If all defaults have been observed, the
        first default value is used as a fallback.
        """
        default_grid = ParameterPlanner._DEFAULT_RANGES
        # Gather observed values per parameter from the history
        observed: Dict[str, set] = {name: set() for name in default_grid}
        for entry in history.get_all():
            param_dict = dict(entry.parameters)
            for name, val in param_dict.items():
                if name in observed:
                    observed[name].add(val)
        # Build candidate parameters deterministically
        candidate_params: Dict[str, Any] = {}
        for name in sorted(default_grid.keys()):
            defaults = list(default_grid[name])
            seen = observed.get(name, set())
            unseen = [v for v in defaults if v not in seen]
            if unseen:
                sample = defaults[0]
                # Choose based on the value type
                if isinstance(sample, float):
                    # For floats, pick the furthest (last) unseen value
                    candidate_params[name] = unseen[-1]
                elif isinstance(sample, int):
                    # For ints, pick the nearest (first) unseen value
                    candidate_params[name] = unseen[0]
                else:
                    # Booleans or other types – default to the last unseen
                    candidate_params[name] = unseen[-1]
            else:
                candidate_params[name] = defaults[0]
        return [SearchCandidate(parameters=candidate_params)]
