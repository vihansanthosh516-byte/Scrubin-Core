"""Immutable meta‑pattern model for deterministic meta‑learning.

All fields are frozen. New patterns are created via the helper functions in this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace, field
from typing import Tuple


def deterministic_meta_pattern_id(statement: str, supporting_reflections: Tuple[str, ...], supporting_counterfactuals: Tuple[str, ...]) -> str:
    """Deterministic identifier for a meta‑pattern.

    The ID is derived from a SHA‑256 hash over a canonical JSON representation of the
    statement and the sorted list of all supporting IDs (reflections + counterfactuals).
    The first 12 hex characters are prefixed with ``meta-``.
    """
    supporting_all = tuple(sorted(supporting_reflections + supporting_counterfactuals))
    canonical = json.dumps({"statement": statement, "supporting_ids": supporting_all}, separators=(",", ":"), sort_keys=True)
    return f"meta-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_meta_pattern_hash(meta: "MetaPattern") -> str:
    """Deterministic replay hash for a fully populated ``MetaPattern``.
    """
    data = {
        "id": meta.id,
        "statement": meta.statement,
        "confidence": meta.confidence,
        "support_count": meta.support_count,
        "supporting_reflections": list(meta.supporting_reflections),
        "supporting_counterfactuals": list(meta.supporting_counterfactuals),
        "first_seen_tick": meta.first_seen_tick,
        "last_seen_tick": meta.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class MetaPattern:
    """Immutable meta‑learning pattern derived from reflections and counterfactuals."""
    id: str
    statement: str
    confidence: float
    support_count: int
    supporting_reflections: Tuple[str, ...]
    supporting_counterfactuals: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        statement: str,
        confidence: float,
        support_count: int,
        supporting_reflections: Tuple[str, ...] = (),
        supporting_counterfactuals: Tuple[str, ...] = (),
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
    ) -> "MetaPattern":
        """Factory that creates a deterministic ``MetaPattern``.
        """
        meta_id = deterministic_meta_pattern_id(statement, supporting_reflections, supporting_counterfactuals)
        placeholder = MetaPattern(
            id=meta_id,
            statement=statement,
            confidence=confidence,
            support_count=support_count,
            supporting_reflections=supporting_reflections,
            supporting_counterfactuals=supporting_counterfactuals,
            first_seen_tick=first_seen_tick,
            last_seen_tick=last_seen_tick,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_meta_pattern_hash(placeholder))
