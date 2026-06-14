"""Append‑only store for deterministic counterfactual scenarios and results.

The store never mutates existing entries. It provides simple retrieval and a basic
statistics method useful for debugging/benchmarking.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Iterable, List, Tuple

from .counterfactual import CounterfactualScenario, CounterfactualResult


class CounterfactualStore:
    """Immutable, append‑only storage for counterfactual analysis.

    The store maintains two internal lists – one for scenarios and one for the
    corresponding results. Items are never removed or mutated. ``add`` verifies
    that a result matches its scenario and raises ``ValueError`` on mismatch.
    """

    def __init__(self) -> None:
        self._scenarios: List[CounterfactualScenario] = []
        self._results: List[CounterfactualResult] = []

    # ---------------------------------------------------------------------
    # Append operations
    # ---------------------------------------------------------------------
    def add(self, scenario: CounterfactualScenario, result: CounterfactualResult) -> None:
        """Append ``scenario`` and ``result`` atomically.

        The ``result`` must reference the ``scenario.id``. The method raises a
        ``ValueError`` if the IDs mismatch.
        """
        if result.scenario_id != scenario.id:
            raise ValueError(
                f"Result scenario_id {result.scenario_id!r} does not match scenario id {scenario.id!r}"
            )
        # Append in order: scenario then result. No mutation of existing items.
        self._scenarios.append(scenario)
        self._results.append(result)

    # ---------------------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------------------
    def scenarios(self) -> Tuple[CounterfactualScenario, ...]:
        """Return an immutable view of stored scenarios."""
        return tuple(self._scenarios)

    def results(self) -> Tuple[CounterfactualResult, ...]:
        """Return an immutable view of stored results."""
        return tuple(self._results)

    def query_by_episode(self, episode_id: str) -> Tuple[Tuple[CounterfactualScenario, CounterfactualResult], ...]:
        """Return all (scenario, result) pairs that originate from ``episode_id``.
        """
        pairs = []
        for scen, res in zip(self._scenarios, self._results):
            if scen.source_episode_id == episode_id:
                pairs.append((scen, res))
        return tuple(pairs)

    # ---------------------------------------------------------------------
    # Statistics – useful for debugging or performance checks.
    # ---------------------------------------------------------------------
    def statistics(self) -> dict:
        """Return simple statistics about the store.

        The dict includes ``scenario_count``, ``result_count`` and a histogram of
        ``confidence`` buckets (low/medium/high). This method never raises.
        """
        scenario_count = len(self._scenarios)
        result_count = len(self._results)
        # Confidence distribution – bucket thresholds are arbitrary but useful.
        conf_counter = Counter()
        for scen in self._scenarios:
            if scen.confidence < 0.33:
                conf_counter["low"] += 1
            elif scen.confidence < 0.66:
                conf_counter["medium"] += 1
            else:
                conf_counter["high"] += 1
        return {
            "scenario_count": scenario_count,
            "result_count": result_count,
            "confidence_distribution": dict(conf_counter),
        }
