"""Immutable belief model for deterministic reasoning.

All fields are frozen; updates are performed by creating a new instance via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_belief_id(statement: str, supporting_facts: Tuple[str, ...]) -> str:
    """Deterministic identifier for a belief.

    The ID is derived from a SHA‑256 hash over a canonical JSON representation of the
    statement and the sorted list of supporting fact IDs. Only the first 12 hex
    characters are kept (prefixed with ``belief-``) for brevity while ensuring
    deterministic uniqueness.
    """
    canonical = json.dumps(
        {"statement": statement, "supporting_facts": sorted(supporting_facts)},
        separators=(",", ":"),
        sort_keys=True,
    )
    return "belief-" + hashlib.sha256(canonical.encode()).hexdigest()[:12]


def deterministic_belief_hash(belief: "Belief") -> str:
    """Deterministic replay hash for a fully populated ``Belief``.

    The hash includes all semantic fields and is computed from a compact deterministic
    JSON representation.
    """
    data = {
        "id": belief.id,
        "statement": belief.statement,
        "supporting_facts": list(belief.supporting_facts),
        "support_count": belief.support_count,
        "confidence": belief.confidence,
        "first_seen_tick": belief.first_seen_tick,
        "last_seen_tick": belief.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class Belief:
    """Immutable belief derived from aggregated semantic facts."""
    id: str
    statement: str
    supporting_facts: Tuple[str, ...]
    support_count: int
    confidence: float
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        statement: str,
        fact_id: str,
        fact_confidence: float,
        tick: int,
        prior: "Belief | None" = None,
    ) -> "Belief":
        """Factory that builds or merges a belief from a single supporting fact.

        Parameters
        ----------
        statement: deterministic statement string.
        fact_id: ID of the supporting ``SemanticFact``.
        fact_confidence: Confidence of that fact.
        tick: Current simulation tick.
        prior: Existing belief to merge with, if any.
        """
        if prior is None:
            # Use the fact_id as the belief identifier for deterministic replay (preserves original IDs)
            belief_id = fact_id
            return Belief(
                id=belief_id,
                statement=statement,
                supporting_facts=(fact_id,),
                support_count=1,
                confidence=fact_confidence,
                first_seen_tick=tick,
                last_seen_tick=tick,
                replay_hash="",
            )
        # Merge with existing belief
        total_conf = prior.confidence * prior.support_count + fact_confidence
        new_support = prior.support_count + 1
        new_conf = total_conf / new_support
        merged = Belief(
            id=prior.id,
            statement=prior.statement,
            supporting_facts=prior.supporting_facts + (fact_id,),
            support_count=new_support,
            confidence=new_conf,
            first_seen_tick=min(prior.first_seen_tick, tick),
            last_seen_tick=max(prior.last_seen_tick, tick),
            replay_hash="",
        )
        return replace(merged, replay_hash=deterministic_belief_hash(merged))
