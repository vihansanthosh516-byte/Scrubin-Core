"""Immutable deterministic strategy model.

The model represents a reusable sequence of actions discovered from completed
plans and executive outcomes. All fields are frozen; new instances are created
via the factory methods which compute deterministic identifiers and replay hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_strategy_id(name: str, action_sequence: Tuple[str, ...], supporting_plan_ids: Tuple[str, ...]) -> str:
    """Deterministic identifier for a ``Strategy``.

    The ID is ``strategy-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the ``name``, ``action_sequence`` and the sorted
    list of supporting plan IDs.
    """
    canonical = json.dumps(
        {
            "name": name,
            "action_sequence": list(action_sequence),
            "supporting_plan_ids": sorted(supporting_plan_ids),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"strategy-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_strategy_hash(strategy: "Strategy") -> str:
    """Deterministic replay hash for a fully populated ``Strategy``.
    """
    data = {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "trigger_conditions": list(strategy.trigger_conditions),
        "action_sequence": list(strategy.action_sequence),
        "success_count": strategy.success_count,
        "failure_count": strategy.failure_count,
        "confidence": strategy.confidence,
        "supporting_plan_ids": list(strategy.supporting_plan_ids),
        "first_seen_tick": strategy.first_seen_tick,
        "last_seen_tick": strategy.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class Strategy:
    """Immutable deterministic strategy discovered from the cognition pipeline.

    ``trigger_conditions`` – tuple of strings describing when the strategy should be applied.
    ``action_sequence`` – ordered tuple of action names.
    ``supporting_plan_ids`` – tuple of plan identifiers that contributed to this strategy.
    """
    id: str
    name: str
    description: str
    trigger_conditions: Tuple[str, ...]
    action_sequence: Tuple[str, ...]
    success_count: int
    failure_count: int
    confidence: float
    supporting_plan_ids: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        name: str,
        description: str,
        trigger_conditions: Tuple[str, ...] = (),
        action_sequence: Tuple[str, ...] = (),
        success_count: int = 0,
        failure_count: int = 0,
        confidence: float = 0.0,
        supporting_plan_ids: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "Strategy":
        """Factory that creates a deterministic ``Strategy`` instance.
        """
        strategy_id = deterministic_strategy_id(name, action_sequence, supporting_plan_ids)
        placeholder = Strategy(
            id=strategy_id,
            name=name,
            description=description,
            trigger_conditions=trigger_conditions,
            action_sequence=action_sequence,
            success_count=success_count,
            failure_count=failure_count,
            confidence=confidence,
            supporting_plan_ids=supporting_plan_ids,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_strategy_hash(placeholder))
