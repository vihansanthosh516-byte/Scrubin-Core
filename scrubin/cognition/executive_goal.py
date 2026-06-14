"""Immutable deterministic executive goal model.

All fields are frozen – new goals are created via ``ExecutiveGoal.create`` which
assigns a deterministic ``id`` and ``replay_hash``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_executive_goal_id(description: str, supporting_patterns: Tuple[str, ...], supporting_beliefs: Tuple[str, ...]) -> str:
    """Deterministic identifier for an ``ExecutiveGoal``.

    The ID is ``goal-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the description and the sorted list of all
    supporting IDs (patterns + beliefs).
    """
    supporting_all = tuple(sorted(supporting_patterns + supporting_beliefs))
    canonical = json.dumps(
        {"description": description, "supporting_ids": supporting_all},
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"goal-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_executive_goal_hash(goal: "ExecutiveGoal") -> str:
    """Deterministic replay hash for a fully populated ``ExecutiveGoal``.
    """
    data = {
        "id": goal.id,
        "description": goal.description,
        "priority": goal.priority,
        "confidence": goal.confidence,
        "status": goal.status,
        "supporting_patterns": list(goal.supporting_patterns),
        "supporting_beliefs": list(goal.supporting_beliefs),
        "created_tick": goal.created_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class ExecutiveGoal:
    """Immutable deterministic goal for the autonomous executive layer.

    ``status`` is one of: pending, active, completed, failed, cancelled.
    """
    id: str
    description: str
    priority: float
    confidence: float
    status: str
    supporting_patterns: Tuple[str, ...]
    supporting_beliefs: Tuple[str, ...]
    created_tick: int
    replay_hash: str

    @staticmethod
    def create(
        description: str,
        priority: float,
        confidence: float,
        status: str,
        supporting_patterns: Tuple[str, ...] = (),
        supporting_beliefs: Tuple[str, ...] = (),
        created_tick: int = 0,
    ) -> "ExecutiveGoal":
        """Factory that creates a deterministic ``ExecutiveGoal``.
        """
        goal_id = deterministic_executive_goal_id(description, supporting_patterns, supporting_beliefs)
        placeholder = ExecutiveGoal(
            id=goal_id,
            description=description,
            priority=priority,
            confidence=confidence,
            status=status,
            supporting_patterns=supporting_patterns,
            supporting_beliefs=supporting_beliefs,
            created_tick=created_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_executive_goal_hash(placeholder))
