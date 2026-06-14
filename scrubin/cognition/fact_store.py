"""Append‑only deterministic store for ``SemanticFact`` objects.

Provides O(1) lookup for exact predicate/subject/object triples and deterministic
query ordering. All updates produce a new immutable ``SemanticFact`` instance –
the store itself mutates only by replacing the reference at a fixed index.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Tuple, Optional

from .semantic_fact import SemanticFact


class FactStore:
    """Deterministic, append‑only store for semantic facts.

    * ``facts`` – immutable tuple in insertion order.
    * ``_index`` – maps ``(predicate, subject, object)`` to the fact's list index.
    * ``_total_episodes`` – number of episodes observed (used for confidence).
    """

    def __init__(self) -> None:
        self._facts: List[SemanticFact] = []
        self._index: Dict[Tuple[str, str, str], int] = {}
        self._total_episodes: int = 0

    # ---------------------------------------------------------------------
    # Core mutation API – deterministic and append‑only
    # ---------------------------------------------------------------------
    def record_episode(self) -> None:
        """Increment the total episode counter.

        Must be called exactly once per processed episode before any fact updates.
        """
        self._total_episodes += 1

    @property
    def total_episodes(self) -> int:
        return self._total_episodes

    def add_or_update(self, fact: SemanticFact) -> None:
        """Add a new fact or update an existing one.

        If a fact with the same ``(predicate, subject, object)`` already exists, the
        store creates a new ``SemanticFact`` instance with merged support information
        (using ``SemanticFact.create``) and replaces the entry in place. The insertion
        order stays deterministic – the fact retains its original position.
        """
        key = (fact.predicate, fact.subject, fact.object)
        if key in self._index:
            idx = self._index[key]
            prior = self._facts[idx]
            # Merge prior with new supporting episode.
            merged = SemanticFact.create(
                predicate=fact.predicate,
                subject=fact.subject,
                object_=fact.object,
                episode_id=fact.supporting_episodes[0],  # current episode id
                tick=fact.first_seen_tick,
                total_episodes=self._total_episodes,
                prior=prior,
            )
            # Preserve deterministic ordering: replace at same index.
            self._facts[idx] = merged
        else:
            # New fact – create with deterministic ID and hash.
            new_fact = SemanticFact.create(
                predicate=fact.predicate,
                subject=fact.subject,
                object_=fact.object,
                episode_id=fact.supporting_episodes[0],
                tick=fact.first_seen_tick,
                total_episodes=self._total_episodes,
                prior=None,
            )
            self._facts.append(new_fact)
            self._index[key] = len(self._facts) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def facts(self) -> Tuple[SemanticFact, ...]:
        """Return an immutable view of all stored facts in insertion order."""
        return tuple(self._facts)

    def query(
        self,
        predicate: Optional[str] = None,
        subject: Optional[str] = None,
        object: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> Tuple[SemanticFact, ...]:
        """Return facts matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that dimension.
        The result preserves the original deterministic insertion order.
        """
        result: List[SemanticFact] = []
        for fact in self._facts:
            if predicate is not None and fact.predicate != predicate:
                continue
            if subject is not None and fact.subject != subject:
                continue
            if object is not None and fact.object != object:
                continue
            if min_confidence is not None and fact.confidence < min_confidence:
                continue
            result.append(fact)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def fact_count(self) -> int:
        return len(self._facts)

    def mean_confidence(self) -> float:
        if not self._facts:
            return 0.0
        total = sum(f.confidence for f in self._facts)
        return total / len(self._facts)

    def summary(self) -> Tuple[int, float]:
        """Return ``(fact_count, mean_confidence)`` for quick reporting."""
        return (self.fact_count(), self.mean_confidence())
