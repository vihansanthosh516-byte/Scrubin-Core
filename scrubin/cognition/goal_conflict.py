"""Goal conflict data structures for deterministic arbitration.

The conflict model captures a pairwise conflict between two goals, its type,
severity and timestamps.  The corresponding state container tracks active,
resolved and historic conflicts, together with an arbitration tick.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, Optional


@dataclass(frozen=True)
class GoalConflict:
    """Immutable representation of a conflict between two goals.

    * ``goal_a_id`` and ``goal_b_id`` reference the conflicting goal identifiers.
    * ``conflict_type`` describes the category (e.g., ``"resource"``).
    * ``severity`` influences the arbitration scoring – higher severity penalises
      both goals.
    """

    id: str
    goal_a_id: str
    goal_b_id: str
    conflict_type: str  # e.g. "resource", "physiologic", "strategic"
    severity: float = 1.0
    description: str = ""
    detected_tick: int = 0
    resolved_tick: Optional[int] = None


@dataclass(frozen=True)
class GoalConflictState:
    """Container for deterministic conflict handling.

    * ``active_conflicts`` – currently unresolved conflicts.
    * ``resolved_conflicts`` – conflicts that have been arbitrated.
    * ``conflict_history`` – chronological record of all conflicts.
    * ``arbitration_tick`` – tick counter for the arbitration subsystem.
    """

    active_conflicts: Tuple[GoalConflict, ...] = field(default_factory=tuple)
    resolved_conflicts: Tuple[GoalConflict, ...] = field(default_factory=tuple)
    conflict_history: Tuple[GoalConflict, ...] = field(default_factory=tuple)
    arbitration_tick: int = 0

    # ---------------------------------------------------------------------
    # Helper to produce deterministic ordering key for conflicts.
    # ---------------------------------------------------------------------
    @staticmethod
    def _conflict_sort_key(conflict: GoalConflict):
        # severity desc, then type asc, then id asc
        return (-conflict.severity, conflict.conflict_type, conflict.id)

    def add_conflict(self, conflict: GoalConflict) -> "GoalConflictState":
        """Add a new conflict to the active set (if not already present)."""
        if any(c.id == conflict.id for c in self.active_conflicts):
            return self
        new_active = tuple(sorted(self.active_conflicts + (conflict,), key=self._conflict_sort_key))
        new_history = tuple(sorted(self.conflict_history + (conflict,), key=self._conflict_sort_key))
        return replace(self, active_conflicts=new_active, conflict_history=new_history)

    def resolve_conflict(self, conflict_id: str) -> "GoalConflictState":
        """Mark a conflict as resolved – moves it to ``resolved_conflicts``.

        The ``resolved_tick`` is set to the current ``arbitration_tick``.
        """
        conflict = next((c for c in self.active_conflicts if c.id == conflict_id), None)
        if not conflict:
            return self
        # Record resolution tick
        resolved = replace(conflict, resolved_tick=self.arbitration_tick)
        new_active = tuple(c for c in self.active_conflicts if c.id != conflict_id)
        new_resolved = tuple(sorted(self.resolved_conflicts + (resolved,), key=self._conflict_sort_key))
        return replace(self, active_conflicts=new_active, resolved_conflicts=new_resolved)

    def with_arbitration_tick(self, tick: int) -> "GoalConflictState":
        return replace(self, arbitration_tick=tick)

    # Placeholder – can be expanded for more sophisticated logic.
    def compute_dominant_resolution(self) -> "GoalConflictState":
        return self
