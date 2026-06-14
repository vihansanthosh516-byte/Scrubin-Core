"""Deterministic reflection generation from ``BeliefStore``.

Groups beliefs by subject (first word of the statement) and creates a higher‑level
reflection when a subject appears in two or more beliefs. Deterministic templates
are used; no randomness, NLP, or learning.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .belief_store import BeliefStore
from .reflection_store import ReflectionStore
from .reflection import Reflection


def _group_beliefs_by_subject(belief_store: BeliefStore) -> Dict[str, List]:
    """Group beliefs by the first token (subject) of the statement.

    Returns a mapping from subject string to a list of ``Belief`` objects.
    """
    groups: defaultdict[str, List] = defaultdict(list)
    for belief in belief_store.beliefs:
        subject = belief.statement.split()[0]
        groups[subject].append(belief)
    return groups


def update_reflections_from_beliefs(belief_store: BeliefStore, reflection_store: ReflectionStore) -> None:
    """Create or merge reflections based on the current ``BeliefStore``.

    For each subject with at least two beliefs a deterministic reflection is
    generated using the template::

        "<subject> leads to multiple effects"

    Confidence is the mean of belief confidences. The function updates the
    ``ReflectionStore`` in‑place (append‑only semantics).
    """
    groups = _group_beliefs_by_subject(belief_store)
    for subject, beliefs in groups.items():
        if len(beliefs) < 2:
            continue
        statement = f"{subject} leads to multiple effects"
        support_count = len(beliefs)
        confidence = sum(b.confidence for b in beliefs) / support_count
        first_tick = min(b.first_seen_tick for b in beliefs)
        last_tick = max(b.last_seen_tick for b in beliefs)
        supporting_ids = tuple(b.id for b in beliefs)
        placeholder = Reflection(
            id="",
            statement=statement,
            supporting_beliefs=supporting_ids,
            support_count=support_count,
            confidence=confidence,
            first_seen_tick=first_tick,
            last_seen_tick=last_tick,
            replay_hash="",
        )
        reflection_store.add_or_update(placeholder)
