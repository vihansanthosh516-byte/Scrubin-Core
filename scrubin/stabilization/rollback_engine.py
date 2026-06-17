"""Deterministic rollback decision engine.

Selects a prior stable snapshot (represented by its deterministic hash) when
instability is detected.  Selection is purely based on hash ordering – the
smallest hash among known stable snapshots is chosen.
"""

from __future__ import annotations

from .models import RollbackState


class RollbackEngine:
    @staticmethod
    def evaluate(state: any, stable_hashes: tuple[int, ...]) -> RollbackState:
        # If no stable snapshots are known, no rollback.
        if not stable_hashes:
            return RollbackState(required=False, target_hash=0)
        # Deterministically select the minimal hash as the rollback target.
        target = min(stable_hashes)
        # Require rollback if current state's hash differs from target.
        current_hash = getattr(state, "deterministic_hash", 0)
        required = current_hash != target
        return RollbackState(required=required, target_hash=target)
