"""SystemIntegrationEngine – merges subsystem snapshots into a CrossLayerSnapshot.
All operations are pure and deterministic.  No mutation of the input snapshots
occurs; the resulting ``CrossLayerSnapshot`` aggregates the deterministic hashes
of the provided snapshots in a deterministic order.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import CrossLayerSnapshot, IntegrationReport


class SystemIntegrationEngine:
    @staticmethod
    def integrate(
        learning_snapshot: Any = None,
        adaptive_snapshot: Any = None,
        meta_snapshot: Any = None,
        simulation_snapshot: Any = None,
        scenario_snapshot: Any = None,
        evaluation_snapshot: Any = None,
        stabilization_snapshot: Any = None,
    ) -> Tuple[CrossLayerSnapshot, IntegrationReport]:
        """Combine the provided snapshots into a ``CrossLayerSnapshot``.

        * Verify that each snapshot (if provided) implements ``deterministic_hash``.
        * Compute a combined deterministic hash by concatenating the individual
          hashes sorted by subsystem name.
        * Produce an ``IntegrationReport`` describing any missing snapshots or
          missing hash attributes.
        """
        # Detect missing layers
        names = [
            "learning",
            "adaptive",
            "meta",
            "simulation",
            "scenario",
            "evaluation",
            "stabilization",
        ]
        snapshots = [
            learning_snapshot,
            adaptive_snapshot,
            meta_snapshot,
            simulation_snapshot,
            scenario_snapshot,
            evaluation_snapshot,
            stabilization_snapshot,
        ]
        missing = [n for n, s in zip(names, snapshots) if s is None]
        issues: Tuple[str, ...] = ()
        if missing:
            issues = (*issues, f"missing:{','.join(sorted(missing))}")

        # Verify deterministic_hash attribute
        for n, s in zip(names, snapshots):
            if s is not None and not hasattr(s, "deterministic_hash"):
                issues = (*issues, f"no_hash:{n}")

        # Compute combined hash deterministically – sort by name to guarantee ordering.
        hash_parts = []
        for n, s in zip(names, snapshots):
            if s is not None:
                h = getattr(s, "deterministic_hash", 0)
                hash_parts.append((n, h))
        # Sort by subsystem name (already in that order, but enforce for safety).
        hash_parts.sort(key=lambda x: x[0])
        combined_int = 0
        for _, h in hash_parts:
            # Combine using XOR to stay deterministic and order‑independent after sorting.
            combined_int ^= h

        # Build CrossLayerSnapshot (immutable). Use replace() pattern if needed – we construct directly.
        cross = CrossLayerSnapshot(
            learning_snapshot=learning_snapshot,
            adaptive_snapshot=adaptive_snapshot,
            meta_snapshot=meta_snapshot,
            simulation_snapshot=simulation_snapshot,
            scenario_snapshot=scenario_snapshot,
            evaluation_snapshot=evaluation_snapshot,
            stabilization_snapshot=stabilization_snapshot,
            combined_hash=combined_int,
        )
        report = IntegrationReport(issues=issues, hash_consistency=len(issues) == 0)
        return cross, report
