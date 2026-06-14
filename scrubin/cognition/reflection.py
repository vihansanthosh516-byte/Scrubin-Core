"""Immutable reflection model for deterministic reasoning.

A reflection aggregates supporting beliefs and produces a higher‑order statement.
All fields are frozen; updates are performed via ``dataclasses.replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_reflection_id(statement: str, supporting_beliefs: Tuple[str, ...]) -> str:
    """Deterministic identifier for a reflection.

    The ID is derived from a SHA‑256 hash over a canonical JSON representation of the
    statement and the sorted list of supporting belief IDs. Only the first 12 hex
    characters are kept (plus ``reflection-`` prefix) to keep IDs short while remaining
    globally unique for replay.
    """
    canonical = json.dumps(
        {"statement": statement, "supporting_beliefs": sorted(supporting_beliefs)},
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"reflection-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_reflection_hash(reflection: "Reflection") -> str:
    """Deterministic replay hash for a fully populated ``Reflection``.

    The hash covers all semantic fields of the reflection, serialized as a compact
    JSON with deterministic key order.
    """
    data = {
        "id": reflection.id,
        "statement": reflection.statement,
        "supporting_beliefs": list(reflection.supporting_beliefs),
        "support_count": reflection.support_count,
        "confidence": reflection.confidence,
        "first_seen_tick": reflection.first_seen_tick,
        "last_seen_tick": reflection.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class Reflection:
    """Immutable reflection derived from aggregated beliefs."""
    id: str
    statement: str
    supporting_beliefs: Tuple[str, ...]
    support_count: int
    confidence: float
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        statement: str,
        belief_id: str,
        belief_confidence: float,
        tick: int,
        prior: "Reflection | None" = None,
    ) -> "Reflection":
        """Factory that builds or merges a reflection from a single supporting belief.

        Parameters
        ----------
        statement: deterministic higher‑order statement.
        belief_id: ID of the supporting ``Belief``.
        belief_confidence: Confidence of that belief.
        tick: Current simulation tick.
        prior: Existing reflection to merge with, if any.
        """
        if prior is None:
            refl_id = deterministic_reflection_id(statement, (belief_id,))
            return Reflection(
                id=refl_id,
                statement=statement,
                supporting_beliefs=(belief_id,),
                support_count=1,
                confidence=belief_confidence,
                first_seen_tick=tick,
                last_seen_tick=tick,
                replay_hash="",
            )
        # Merge with existing reflection
        total_conf = prior.confidence * prior.support_count + belief_confidence
        new_support = prior.support_count + 1
        new_conf = total_conf / new_support
        merged = Reflection(
            id=prior.id,
            statement=prior.statement,
            supporting_beliefs=prior.supporting_beliefs + (belief_id,),
            support_count=new_support,
            confidence=new_conf,
            first_seen_tick=min(prior.first_seen_tick, tick),
            last_seen_tick=max(prior.last_seen_tick, tick),
            replay_hash="",
        )
        return replace(merged, replay_hash=deterministic_reflection_hash(merged))
