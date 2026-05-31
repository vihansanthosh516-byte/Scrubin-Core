"""Goal hierarchy data structures for deterministic cognition.

This module introduces immutable, deterministic data structures that model a
hierarchical goal system.  Goal nodes can be added, completed, or abandoned
purely via functional updates, ensuring replay safety.  All collections are stored
as sorted tuples to guarantee deterministic iteration order.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, Optional


@dataclass(frozen=True)
class GoalNode:
    """Immutable representation of a single goal.

    The fields are deliberately simple; they mirror the requirements of the
    Phase O.7.2 specification.  Helper methods ``with_*`` return new copies with
    the requested mutation applied.  Tuple fields are always stored sorted.
    """

    id: str
    parent_goal_id: Optional[str] = None
    goal_type: str = "tactical"
    description: str = ""
    priority: float = 0.0
    urgency: float = 0.0
    confidence: float = 1.0
    progress: float = 0.0
    completion_state: str = "active"
    required_concepts: Tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: Tuple[str, ...] = field(default_factory=tuple)
    created_tick: int = 0
    completed_tick: Optional[int] = None

    # ---------------------------------------------------------------------
    # Helper methods – functional updates returning a new GoalNode.
    # ---------------------------------------------------------------------
    def with_id(self, new_id: str) -> "GoalNode":
        return replace(self, id=new_id)

    def with_parent_goal_id(self, parent_id: Optional[str]) -> "GoalNode":
        return replace(self, parent_goal_id=parent_id)

    def with_goal_type(self, goal_type: str) -> "GoalNode":
        return replace(self, goal_type=goal_type)

    def with_description(self, description: str) -> "GoalNode":
        return replace(self, description=description)

    def with_priority(self, priority: float) -> "GoalNode":
        return replace(self, priority=priority)

    def with_urgency(self, urgency: float) -> "GoalNode":
        return replace(self, urgency=urgency)

    def with_confidence(self, confidence: float) -> "GoalNode":
        return replace(self, confidence=confidence)

    def with_progress(self, progress: float) -> "GoalNode":
        return replace(self, progress=progress)

    def with_completion_state(self, state: str) -> "GoalNode":
        return replace(self, completion_state=state)

    def with_required_concepts(self, concepts: Tuple[str, ...]) -> "GoalNode":
        return replace(self, required_concepts=tuple(sorted(concepts)))

    def with_blocking_conditions(self, conditions: Tuple[str, ...]) -> "GoalNode":
        return replace(self, blocking_conditions=tuple(sorted(conditions)))

    def with_created_tick(self, tick: int) -> "GoalNode":
        return replace(self, created_tick=tick)

    def with_completed_tick(self, tick: Optional[int]) -> "GoalNode":
        return replace(self, completed_tick=tick)


@dataclass(frozen=True)
class GoalHierarchyState:
    """Container for all goal nodes and deterministic selection logic.

    The container mirrors the design of ``IntentiveCognitionState`` – all
    collections are immutable tuples kept sorted by ``id`` to guarantee
    deterministic iteration order.
    """

    active_goals: Tuple[GoalNode, ...] = field(default_factory=tuple)
    completed_goals: Tuple[GoalNode, ...] = field(default_factory=tuple)
    abandoned_goals: Tuple[GoalNode, ...] = field(default_factory=tuple)
    goal_history: Tuple[GoalNode, ...] = field(default_factory=tuple)
    dominant_goal: Optional[GoalNode] = None
    cognition_tick: int = 0

    @property
    def dominant_goal_id(self) -> Optional[str]:
        return self.dominant_goal.id if self.dominant_goal else None

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _unique_goal(self, goal: GoalNode, collection: Tuple[GoalNode, ...]) -> bool:
        return not any(g.id == goal.id for g in collection)

    # ---------------------------------------------------------------------
    # Lifecycle operations – pure functional updates
    # ---------------------------------------------------------------------
    def add_goal(self, goal: GoalNode) -> "GoalHierarchyState":
        """Add ``goal`` to ``active_goals`` and ``goal_history`` if not present.

        Duplicates across all collections are ignored.  The resulting tuples are
        kept sorted by ``id`` for deterministic iteration.
        """
        if not self._unique_goal(goal, self.active_goals):
            return self
        new_active = tuple(sorted(self.active_goals + (goal,), key=lambda x: x.id))
        new_history = tuple(sorted(self.goal_history + (goal,), key=lambda x: x.id))
        return replace(self, active_goals=new_active, goal_history=new_history)

    def complete_goal(self, goal_id: str) -> "GoalHierarchyState":
        """Move an active goal to ``completed_goals`` (no‑op if missing)."""
        goal = next((g for g in self.active_goals if g.id == goal_id), None)
        if not goal:
            return self
        # Mark as completed – retain original fields (progress may be >0)
        completed_goal = goal.with_completion_state("completed").with_completed_tick(self.cognition_tick)
        new_active = tuple(g for g in self.active_goals if g.id != goal_id)
        new_completed = tuple(sorted(self.completed_goals + (completed_goal,), key=lambda x: x.id))
        return replace(self, active_goals=new_active, completed_goals=new_completed)

    def abandon_goal(self, goal_id: str) -> "GoalHierarchyState":
        """Move an active goal to ``abandoned_goals`` (no‑op if missing)."""
        goal = next((g for g in self.active_goals if g.id == goal_id), None)
        if not goal:
            return self
        abandoned_goal = goal.with_completion_state("abandoned").with_completed_tick(self.cognition_tick)
        new_active = tuple(g for g in self.active_goals if g.id != goal_id)
        new_abandoned = tuple(sorted(self.abandoned_goals + (abandoned_goal,), key=lambda x: x.id))
        return replace(self, active_goals=new_active, abandoned_goals=new_abandoned)

    def with_dominant_goal(self, dominant: Optional[GoalNode]) -> "GoalHierarchyState":
        return replace(self, dominant_goal=dominant)

    def with_cognition_tick(self, tick: int) -> "GoalHierarchyState":
        return replace(self, cognition_tick=tick)

    # ---------------------------------------------------------------------
    # Deterministic dominant‑goal computation
    # ---------------------------------------------------------------------
    def compute_dominant_goal(self) -> "GoalHierarchyState":
        """Select the dominant goal deterministically from ``active_goals``.

        Ordering criteria (in priority order):
        1. Highest ``urgency`` (descending)
        2. Highest ``priority`` (descending)
        3. Highest ``confidence`` (descending)
        4. Lexicographically smallest ``id``
        """
        if not self.active_goals:
            return replace(self, dominant_goal=None)
        sorted_goals = sorted(
            self.active_goals,
            key=lambda g: (-g.urgency, -g.priority, -g.confidence, g.id),
        )
        dominant = sorted_goals[0]
        return replace(self, dominant_goal=dominant)
