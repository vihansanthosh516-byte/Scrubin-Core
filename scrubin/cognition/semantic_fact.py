"""Immutable semantic fact model.

All fields are deterministic and frozen. The fact is never mutated; updates create a new
instance via ``dataclasses.replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def _canonical_repr(predicate: str, subject: str, object_: str) -> str:
    """Return a deterministic canonical string used for hashing.

    The components are concatenated in a fixed order with a separator to avoid accidental
    collisions. ``json.dumps`` with ``sort_keys=True`` guarantees deterministic ordering.
    """
    data = {
        "predicate": predicate,
        "subject": subject,
        "object": object_,
    }
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def deterministic_fact_id(predicate: str, subject: str, object_: str) -> str:
    """Generate a stable identifier for a fact.

    Uses SHA‑256 over a canonical representation of the three textual fields.
    Returns ``"fact-"`` + first 12 hex characters of the digest (enough uniqueness for
    deterministic replay while keeping IDs short).
    """
    canonical = _canonical_repr(predicate, subject, object_)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"fact-{digest[:12]}"


def deterministic_fact_hash(fact: "SemanticFact") -> str:
    """Compute a deterministic replay hash for a fully populated ``SemanticFact``.

    The hash includes all fields that affect semantics. ``supporting_episodes`` is
    serialized as a tuple of strings in insertion order.
    """
    # Serialize deterministically – JSON with sorted keys and no whitespace.
    data = {
        "id": fact.id,
        "predicate": fact.predicate,
        "subject": fact.subject,
        "object": fact.object,
        "confidence": fact.confidence,
        "support_count": fact.support_count,
        "supporting_episodes": list(fact.supporting_episodes),
        "first_seen_tick": fact.first_seen_tick,
        "last_seen_tick": fact.last_seen_tick,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class SemanticFact:
    """Immutable, deterministic fact derived from episodes.

    All fields are serialisable and contribute to the deterministic ``replay_hash``.
    ``supporting_episodes`` is a tuple of episode IDs that contributed to the fact.
    """

    id: str
    predicate: str
    subject: str
    object: str
    confidence: float
    support_count: int
    supporting_episodes: Tuple[str, ...]
    first_seen_tick: int
    last_seen_tick: int
    replay_hash: str

    @staticmethod
    def create(
        predicate: str,
        subject: str,
        object_: str,
        episode_id: str,
        tick: int,
        total_episodes: int,
        prior: "SemanticFact | None" = None,
    ) -> "SemanticFact":
        """Factory that builds or updates a fact deterministically.

        If ``prior`` is supplied, the new fact incorporates its state plus the new
        supporting episode. ``total_episodes`` is the number of episodes observed so
        far (including the current one) and is used for Laplace‑smoothed confidence.
        """
        if prior is None:
            support_count = 1
            supporting = (episode_id,)
            first_tick = tick
            last_tick = tick
        else:
            support_count = prior.support_count + 1
            supporting = prior.supporting_episodes + (episode_id,)
            first_tick = min(prior.first_seen_tick, tick)
            last_tick = max(prior.last_seen_tick, tick)

        # Laplace smoothing: (support + 1) / (total + 2)
        confidence = (support_count + 1) / (total_episodes + 2)
        fact_id = deterministic_fact_id(predicate, subject, object_)
        # Build a temporary instance (replay_hash will be filled after)
        tmp = SemanticFact(
            id=fact_id,
            predicate=predicate,
            subject=subject,
            object=object_,
            confidence=confidence,
            support_count=support_count,
            supporting_episodes=supporting,
            first_seen_tick=first_tick,
            last_seen_tick=last_tick,
            replay_hash="",
        )
        # Compute deterministic hash now that the instance is fully populated.
        replay_hash = deterministic_fact_hash(tmp)
        # Return a new frozen instance with the hash set.
        return replace(tmp, replay_hash=replay_hash)
