"""Deterministic meta‑pattern extraction – aggregates reflections and counterfactuals
into higher‑level immutable ``MetaPattern`` objects.

Provides a pure, append‑only operation that never mutates lower‑cognition layers.
"""

from __future__ import annotations

from .meta_pattern import MetaPattern
from .meta_store import MetaStore
from .reflection_store import ReflectionStore
from .counterfactual_store import CounterfactualStore
from .knowledge_graph import KnowledgeGraph


def _reflection_to_meta(reflection) -> MetaPattern:
    """Convert a ``Reflection`` into a ``MetaPattern``."""
    return MetaPattern.create(
        statement=reflection.statement,
        confidence=reflection.confidence,
        support_count=reflection.support_count,
        supporting_reflections=(reflection.id,),
        supporting_counterfactuals=(),
        first_seen_tick=reflection.first_seen_tick,
        last_seen_tick=reflection.last_seen_tick,
    )


def _counterfactual_to_meta(result) -> MetaPattern:
    """Convert a ``CounterfactualResult`` into a ``MetaPattern``.
    Uses a deterministic statement derived from the scenario identifier.
    """
    statement = f"counterfactual:{result.id}"
    return MetaPattern.create(
        statement=statement,
        confidence=result.confidence,
        support_count=1,
        supporting_reflections=(),
        supporting_counterfactuals=(result.id,),
        first_seen_tick=0,
        last_seen_tick=0,
    )


def update_meta_patterns(
    reflection_store: ReflectionStore,
    counterfactual_store: CounterfactualStore,
    knowledge_graph: KnowledgeGraph,
    meta_store: MetaStore,
) -> None:
    """Extract deterministic meta‑patterns from lower‑cognition layers.

    The function is append‑only: it adds new patterns or merges with existing ones
    based on identical statements. The knowledge graph is currently unused but
    retained in the signature for future deterministic pattern rules.
    """
    for refl in reflection_store.reflections:
        meta = _reflection_to_meta(refl)
        meta_store.add_or_update(meta)

    for cf_result in counterfactual_store.results():
        meta = _counterfactual_to_meta(cf_result)
        meta_store.add_or_update(meta)
