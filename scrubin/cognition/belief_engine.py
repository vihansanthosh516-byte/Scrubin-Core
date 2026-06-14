"""Deterministic belief generation from semantic facts.

The engine iterates over all ``SemanticFact`` objects, builds a deterministic
statement (``"subject predicate object"``) and inserts or merges a ``Belief``
into the supplied ``BeliefStore``.
"""

from __future__ import annotations

from .fact_store import FactStore
from .belief_store import BeliefStore
from .belief import Belief


def update_beliefs_from_facts(fact_store: FactStore, belief_store: BeliefStore) -> None:
    """Create or update beliefs based on the current contents of ``fact_store``.

    This function is deterministic: it always processes facts in the order they
    appear in ``fact_store.facts`` (insertion order) and uses a deterministic
    statement construction rule.
    """
    for fact in fact_store.facts:
        # Build a deterministic statement string from the fact components.
        statement = f"{fact.subject} {fact.predicate} {fact.object}"
        # Create a placeholder belief for this single fact.
        placeholder = Belief(
            id="",  # will be assigned inside ``add_or_update``
            statement=statement,
            supporting_facts=(fact.id,),
            support_count=1,
            confidence=fact.confidence,
            first_seen_tick=fact.first_seen_tick,
            last_seen_tick=fact.last_seen_tick,
            replay_hash="",
        )
        belief_store.add_or_update(placeholder)
