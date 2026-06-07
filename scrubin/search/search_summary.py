'''Search summary utilities – deterministic overview of adaptive search state.'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from .experiment_history import HistoryEngine


@dataclass(frozen=True)
class SearchSummary:
    """Aggregated summary of the adaptive search process."""
    total_history: int
    total_recommendations: int
    explored_parameters: Dict[str, int]  # number of unique values observed per parameter
    unexplored_parameters: List[str]
    # Additional metrics could be added here.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_history": self.total_history,
            "total_recommendations": self.total_recommendations,
            "explored_parameters": self.explored_parameters,
            "unexplored_parameters": self.unexplored_parameters,
        }


def generate_summary(
    history_engine: HistoryEngine,
    total_recommendations: int,
    default_grid: Dict[str, Tuple[Any, ...]],
) -> SearchSummary:
    """Generate a deterministic summary of the search state.

    * total_history – number of recorded experiment runs.
    * total_recommendations – number of recommendations generated in the latest search.
    * explored_parameters – mapping parameter name → count of distinct observed values.
    * unexplored_parameters – list of parameter names where not all default values have been observed.
    """
    histories = history_engine.get_all()
    # Count unique observed values per parameter
    observed: Dict[str, set] = {name: set() for name in default_grid}
    for entry in histories:
        param_dict = dict(entry.parameters)
        for name, val in param_dict.items():
            if name in observed:
                observed[name].add(val)
    explored_parameters = {name: len(vals) for name, vals in observed.items() if vals}
    unexplored_parameters = [name for name, vals in observed.items() if set(default_grid[name]) - vals]
    return SearchSummary(
        total_history=len(histories),
        total_recommendations=total_recommendations,
        explored_parameters=explored_parameters,
        unexplored_parameters=unexplored_parameters,
    )
