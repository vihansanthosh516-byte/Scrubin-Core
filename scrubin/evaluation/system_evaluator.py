"""SystemEvaluator – validates presence and hash consistency of subsystem snapshots.
All checks are pure, deterministic, and side‑effect free.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import SystemHealthReport


class SystemEvaluator:
    @staticmethod
    def evaluate(
        executive_snapshot: Any = None,
        physiology_snapshot: Any = None,
        knowledge_snapshot: Any = None,
        memory_snapshot: Any = None,
        learning_snapshot: Any = None,
        simulation_snapshot: Any = None,
        stabilization_snapshot: Any = None,
    ) -> SystemHealthReport:
        """Validate subsystem snapshots.

        * Detect missing layers.
        * Verify each provided snapshot implements ``deterministic_hash``.
        * Ensure, when possible, that all snapshots share the same ``tick`` value.
        The function never mutates its inputs.
        """
        # 1. Missing layer detection
        layer_names = [
            "executive",
            "physiology",
            "knowledge",
            "memory",
            "learning",
            "simulation",
            "stabilization",
        ]
        snapshots = [
            executive_snapshot,
            physiology_snapshot,
            knowledge_snapshot,
            memory_snapshot,
            learning_snapshot,
            simulation_snapshot,
            stabilization_snapshot,
        ]
        missing = [name for name, snap in zip(layer_names, snapshots) if snap is None]
        issues: Tuple[str, ...] = ()
        if missing:
            issues = (*issues, f"missing_layers:{','.join(sorted(missing))}")

        # 2. Hash presence verification
        for name, snap in zip(layer_names, snapshots):
            if snap is not None and not hasattr(snap, "deterministic_hash"):
                issues = (*issues, f"no_hash:{name}")

        # 3. Tick consistency (if all provide a ``tick`` attribute)
        ticks = []
        for snap in snapshots:
            if snap is not None and hasattr(snap, "tick"):
                try:
                    ticks.append(int(getattr(snap, "tick")))
                except Exception:
                    pass
        if ticks and len(set(ticks)) > 1:
            issues = (*issues, "tick_mismatch")

        hash_consistency = len(issues) == 0
        return SystemHealthReport(issues=issues, hash_consistency=hash_consistency)
