"""Deterministic reflection state for decision introspection.

The state captures a chronologically ordered list of ``DecisionReflection``
records and derived drift / stability metrics.  All collections are immutable
tuples sorted to guarantee deterministic iteration order.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, Optional


@dataclass(frozen=True)
class DecisionReflection:
    """Immutable record of a single decision‑making observation.

    * ``goal_id`` – the goal involved (if any).
    * ``intent_id`` – the intent involved (if any).
    * ``conflict_id`` – the conflict identifier (if any).
    * ``outcome`` – categorical outcome label.
    * ``reason_tags`` – deterministic tags describing why the outcome
      occurred.
    * ``confidence`` – confidence of the decision (0.0‑1.0).
    * ``stability_score`` – numeric score used for deterministic ordering.
    """

    id: str
    tick: int
    goal_id: Optional[str] = None
    intent_id: Optional[str] = None
    conflict_id: Optional[str] = None
    outcome: str = ""
    reason_tags: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    stability_score: float = 0.0


@dataclass(frozen=True)
class ReflectionState:
    """Container for deterministic reflection records and metrics.

    * ``reflections`` – ordered tuple of ``DecisionReflection`` entries.
    * ``drift_index`` – aggregate measure of decision drift.
    * ``stability_index`` – derived stability metric (1.0 – min(1, drift)).
    * ``last_reflection_tick`` – the tick of the most recent reflection.
    """

    reflections: Tuple[DecisionReflection, ...] = field(default_factory=tuple)
    drift_index: float = 0.0
    stability_index: float = 1.0
    last_reflection_tick: int = 0

    # ---------------------------------------------------------------------
    # Helper ordering key – tick asc, stability_score desc, id asc
    # ---------------------------------------------------------------------
    @staticmethod
    def _reflection_sort_key(r: DecisionReflection):
        return (r.tick, -r.stability_score, r.id)

    def add_reflection(self, reflection: DecisionReflection) -> "ReflectionState":
        """Add a new ``DecisionReflection`` to the state (if not duplicate)."""
        if any(r.id == reflection.id for r in self.reflections):
            return self
        new_refs = tuple(sorted(self.reflections + (reflection,), key=self._reflection_sort_key))
        return replace(self, reflections=new_refs, last_reflection_tick=reflection.tick)

    def with_drift_index(self, drift: float) -> "ReflectionState":
        return replace(self, drift_index=drift)

    def with_stability_index(self, stability: float) -> "ReflectionState":
        return replace(self, stability_index=stability)

    def compute_deterministic_insight(self) -> "ReflectionState":
        """Recompute drift and stability indices deterministically.

        * Drift is the fraction of non‑"success" reflections.
        * Stability index = 1.0 - min(1.0, drift).
        """
        total = len(self.reflections)
        if total == 0:
            return self
        non_success = sum(1 for r in self.reflections if r.outcome != "success")
        drift = non_success / total
        stability = 1.0 - min(1.0, drift)
        return replace(self, drift_index=drift, stability_index=stability)
