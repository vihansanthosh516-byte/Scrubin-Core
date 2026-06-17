"""Deterministic drift computation engine.

Compares deterministic hashes of various subsystem snapshots to produce a
`DriftVector`.  No randomness – the calculation is purely arithmetic based on
hash differences.
"""

from __future__ import annotations

from typing import Any

from .models import DriftVector


class DriftEngine:
    """Compute deterministic drift metrics between current system snapshots.

    The `state` argument is expected to be a container object that provides the
    following deterministic_hash attributes (or similar hash values):
    * simulation_snapshot
    * evaluation_snapshot
    * memory_snapshot
    * knowledge_snapshot
    * executive_snapshot
    * learning_snapshot
    """

    @staticmethod
    def _hash_diff(a: int, b: int) -> float:
        # Deterministic normalized difference (0‑1 range) using absolute diff.
        diff = abs(a - b)
        # Scale by a large constant to keep values < 1 for typical hash ranges.
        return diff / (2 ** 61)

    @staticmethod
    def compute(state: Any) -> DriftVector:
        # Extract hashes safely; fall back to 0 if missing.
        sim_hash = getattr(state, "simulation_snapshot", 0)
        eval_hash = getattr(state, "evaluation_snapshot", 0)
        mem_hash = getattr(state, "memory_snapshot", 0)
        know_hash = getattr(state, "knowledge_snapshot", 0)
        exec_hash = getattr(state, "executive_snapshot", 0)
        learn_hash = getattr(state, "learning_snapshot", 0)

        structural = DriftEngine._hash_diff(sim_hash, eval_hash)
        behavioral = DriftEngine._hash_diff(exec_hash, learn_hash)
        physiological = DriftEngine._hash_diff(sim_hash, mem_hash)
        cognitive = DriftEngine._hash_diff(know_hash, eval_hash)

        return DriftVector(
            structural_drift=structural,
            behavioral_drift=behavioral,
            physiological_drift=physiological,
            cognitive_drift=cognitive,
        )
