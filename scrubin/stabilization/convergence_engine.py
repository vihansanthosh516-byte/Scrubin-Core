"""Deterministic convergence evaluation engine.

Compares the current deterministic hash with the previous one to decide the
convergence status.
"""

from __future__ import annotations

from .models import ConvergenceReport


class ConvergenceEngine:
    @staticmethod
    def evaluate(previous_hash: int, current_hash: int) -> ConvergenceReport:
        if previous_hash == current_hash:
            status = "fixed_point"
        elif abs(previous_hash - current_hash) < 10:  # deterministic small delta threshold
            status = "oscillation"
        else:
            status = "divergence"
        return ConvergenceReport(status=status, details=(previous_hash, current_hash))
