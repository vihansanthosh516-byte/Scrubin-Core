"""Deterministic fact extraction from ``Episode`` objects.

The builder uses a tiny, deterministic rule set that maps actions to
consequences. It never performs statistical inference or NLP – patterns are
explicitly registered in ``FACT_PATTERNS``.
"""

from __future__ import annotations

from typing import List

from .semantic_fact import SemanticFact
from scrubin.memory.episode import Episode

# ---------------------------------------------------------------------
# Simple deterministic pattern registry
# ---------------------------------------------------------------------
# Each tuple describes a deterministic mapping:
#   (source_type, target_type, predicate)
# ``source_type`` and ``target_type`` are attribute names on ``Episode`` that
# contain a sequence of dataclasses.
# For Phase 3.2 we only need the Action → Consequence pattern.
# Additional patterns can be added later (e.g., Observation → Observation).
# ---------------------------------------------------------------------
FACT_PATTERNS = [
    ("actions", "consequences", "causes"),
    # Future extensions could include:
    # ("observations", "observations", "co_occurs"),
]


def _normalize(text: str) -> str:
    """Canonicalize textual identifiers for deterministic fact keys.

    Lower‑case and replace spaces with underscores. This ensures identical strings
    across runs regardless of formatting choices elsewhere.
    """
    return text.strip().lower().replace(" ", "_")


def extract_facts_from_episode(episode: Episode) -> List[SemanticFact]:
    """Apply deterministic patterns to an ``Episode`` and return candidate facts.

    The returned ``SemanticFact`` objects have placeholder confidence (0.0) and a
    support count of ``1`` – the ``FactStore`` will merge them and recompute the
    deterministic confidence.
    """
    facts: List[SemanticFact] = []
    for src_attr, tgt_attr, predicate in FACT_PATTERNS:
        src_items = getattr(episode, src_attr, [])
        tgt_items = getattr(episode, tgt_attr, [])
        if not src_items or not tgt_items:
            continue
        # Deterministic pairing – zip the two sequences; extra items are ignored.
        # This guarantees O(N) per episode and bounded output size.
        for src, tgt in zip(src_items, tgt_items):
            subject = _normalize(getattr(src, "name", ""))
            obj = _normalize(getattr(tgt, "name", ""))
            if not subject or not obj:
                continue
            # Build a minimal fact – confidence will be recomputed by FactStore.
            placeholder = SemanticFact(
                id="",
                predicate=predicate,
                subject=subject,
                object=obj,
                confidence=0.0,
                support_count=1,
                supporting_episodes=(episode.id,),
                first_seen_tick=episode.tick,
                last_seen_tick=episode.tick,
                replay_hash="",
            )
            facts.append(placeholder)
    return facts


def process_episode(episode: Episode, store: "scrubin.cognition.fact_store.FactStore") -> None:
    """Integrate an ``Episode`` into the ``FactStore``.

    * Increments the store's episode counter.
    * Extracts deterministic facts from the episode.
    * Adds or updates them in the store.
    """
    # Record that we have processed another episode – required for confidence.
    store.record_episode()
    facts = extract_facts_from_episode(episode)
    for fact in facts:
        store.add_or_update(fact)
