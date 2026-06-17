"""SimulationDriftEngine – compares expected vs actual simulation snapshots.
All drift values are derived from deterministic differences of the two snapshots'
``deterministic_hash`` values.
"""

from __future__ import annotations

from typing import Any

from .models import SimulationDriftReport


class SimulationDriftEngine:
    @staticmethod
    def evaluate(actual_snapshot: Any = None, expected_snapshot: Any = None) -> SimulationDriftReport:
        """Compute deterministic drift metrics.

        The engine computes a numeric difference between the two snapshots' hashes
        and deterministically maps that difference onto six drift categories.
        If the ``expected_snapshot`` is ``None`` the drift is considered zero.
        """
        if actual_snapshot is None:
            # No actual data – no drift.
            return SimulationDriftReport()
        actual_hash = (
            actual_snapshot.deterministic_hash
            if hasattr(actual_snapshot, "deterministic_hash")
            else 0
        )
        expected_hash = (
            expected_snapshot.deterministic_hash
            if expected_snapshot is not None and hasattr(expected_snapshot, "deterministic_hash")
            else actual_hash
        )
        diff = abs(actual_hash - expected_hash)
        # Deterministically split the integer difference into six buckets.
        structural = diff % 10
        behavioral = (diff // 10) % 10
        physiological = (diff // 100) % 10
        executive = (diff // 1000) % 10
        knowledge = (diff // 10000) % 10
        memory = (diff // 100000) % 10
        return SimulationDriftReport(
            structural_drift=structural,
            behavioral_drift=behavioral,
            physiological_drift=physiological,
            executive_drift=executive,
            knowledge_drift=knowledge,
            memory_drift=memory,
        )
