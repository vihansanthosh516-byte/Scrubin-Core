"""Semantic Intent Graph – deterministic procedural execution plan.

The intent graph is a *directed acyclic* representation of the operative plan.
Each node corresponds to a high‑level intent (e.g., "ControlHemorrhage") and
stores the deterministic data required for execution, decomposition, and
fallback handling.

All nodes are immutable – the engine creates new ``IntentGraph`` instances via
``replace``.  This preserves the replay‑safe nature of the entire system.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, Optional


# ---------------------------------------------------------------------------
# Node definition – represents a single procedural intent.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentNode:
    """Immutable representation of a single procedural intent.

    * ``intent_id`` – unique identifier (e.g. ``"control_hemorrhage"``).
    * ``parent_id`` – ``None`` for top‑level intents.
    * ``child_ids`` – tuple of immediate sub‑intents.
    * ``required_concepts`` – tuple of ontology concept ids needed to fulfil the intent.
    * ``blocking_conditions`` – tuple of conditions (as strings) that must be
      false before execution can proceed.
    * ``expected_state`` – deterministic snapshot description of the world
      after successful execution (stored as a string for simplicity).
    * ``anticipated_complications`` – tuple of complication concept ids that may
      arise if the intent fails.
    * ``fallback_paths`` – tuple of alternative intent ids to invoke on failure.
    * ``confidence`` – deterministic confidence score (0.0‑1.0).
    * ``completion_state`` – ``"pending"``, ``"completed"`` or ``"failed"``.
    * ``semantic_priority`` – integer used for deterministic ordering.
    """

    intent_id: str
    parent_id: Optional[str] = None
    child_ids: Tuple[str, ...] = field(default_factory=tuple)
    required_concepts: Tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: Tuple[str, ...] = field(default_factory=tuple)
    expected_state: str = ""
    anticipated_complications: Tuple[str, ...] = field(default_factory=tuple)
    fallback_paths: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 1.0
    completion_state: str = "pending"
    semantic_priority: int = 0

    # -----------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable node.
    # -----------------------------------------------------------------
    def with_parent(self, parent_id: Optional[str]) -> "IntentNode":
        return replace(self, parent_id=parent_id)

    def with_children(self, children: Tuple[str, ...]) -> "IntentNode":
        return replace(self, child_ids=children)

    def add_child(self, child_id: str) -> "IntentNode":
        return replace(self, child_ids=self.child_ids + (child_id,))

    def with_required_concepts(self, concepts: Tuple[str, ...]) -> "IntentNode":
        return replace(self, required_concepts=concepts)

    def with_blocking_conditions(self, conditions: Tuple[str, ...]) -> "IntentNode":
        return replace(self, blocking_conditions=conditions)

    def with_expected_state(self, state: str) -> "IntentNode":
        return replace(self, expected_state=state)

    def with_anticipated_complications(self, comps: Tuple[str, ...]) -> "IntentNode":
        return replace(self, anticipated_complications=comps)

    def with_fallback_paths(self, paths: Tuple[str, ...]) -> "IntentNode":
        return replace(self, fallback_paths=paths)

    def with_confidence(self, conf: float) -> "IntentNode":
        return replace(self, confidence=max(0.0, min(1.0, conf)))

    def with_completion_state(self, state: str) -> "IntentNode":
        return replace(self, completion_state=state)

    def with_priority(self, priority: int) -> "IntentNode":
        return replace(self, semantic_priority=priority)


# ---------------------------------------------------------------------------
# Graph container – immutable collection of intents.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentGraph:
    """Deterministic container for the entire procedural intent hierarchy.

    * ``intents`` – tuple of ``IntentNode`` objects.
    * ``active_intent_ids`` – tuple of intent ids that are currently in focus.
    * ``graph_tick`` – simulation tick associated with this graph.
    """

    intents: Tuple[IntentNode, ...] = field(default_factory=tuple)
    active_intent_ids: Tuple[str, ...] = field(default_factory=tuple)
    graph_tick: int = 0

    # -----------------------------------------------------------------
    # Helper look‑ups and mutation helpers.
    # -----------------------------------------------------------------
    def get_intent(self, intent_id: str) -> IntentNode | None:
        for i in self.intents:
            if i.intent_id == intent_id:
                return i
        return None

    def replace_intent(self, intent: IntentNode) -> "IntentGraph":
        # Remove any existing intent with the same id and insert the updated one.
        filtered = tuple(i for i in self.intents if i.intent_id != intent.intent_id)
        # Deterministic ordering – sort by intent_id after replacement.
        new_intents = tuple(sorted(filtered + (intent,), key=lambda x: x.intent_id))
        return replace(self, intents=new_intents)

    def add_intent(self, intent: IntentNode) -> "IntentGraph":
        if any(i.intent_id == intent.intent_id for i in self.intents):
            # Duplicate – ignore (deterministic no‑op).
            return self
        new_intents = tuple(sorted(self.intents + (intent,), key=lambda x: x.intent_id))
        return replace(self, intents=new_intents)

    def with_active_intents(self, active_ids: Tuple[str, ...]) -> "IntentGraph":
        return replace(self, active_intent_ids=tuple(sorted(active_ids)))

    def with_graph_tick(self, tick: int) -> "IntentGraph":
        return replace(self, graph_tick=tick)

    # -----------------------------------------------------------------
    # Deterministic derivations – e.g., compute root intents.
    # -----------------------------------------------------------------
    def root_intents(self) -> Tuple[IntentNode, ...]:
        roots = [i for i in self.intents if i.parent_id is None]
        return tuple(sorted(roots, key=lambda x: x.intent_id))

    def pending_intents(self) -> Tuple[IntentNode, ...]:
        pending = [i for i in self.intents if i.completion_state == "pending"]
        return tuple(sorted(pending, key=lambda x: (x.semantic_priority, x.intent_id)))
