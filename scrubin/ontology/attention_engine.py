from __future__ import annotations

"""Deterministic executive attention engine.

The engine reads the current ``WorldState`` and produces a new ``WorldState``
with an updated :class:`AttentionState`.  The algorithm is deliberately
minimal – it selects the highest‑priority active concepts up to the configured
capacity, flags overload, and emits a small set of deterministic timeline
events required by the specification.
"""

from typing import List, Tuple

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.active_graph import ActiveSemanticGraph


class AttentionEngine:
    """Engine that deterministically allocates attention each tick.

    The implementation follows the specification:

    * Selects concepts based on activation score (descending) with a deterministic
      tie‑break on ``concept_id``.
    * Updates ``focused_concepts`` and ``suppressed_concepts`` according to the
      configured ``attention_capacity``.
    * Emits events for overload, fixation detection and context‑switch
      penalties.
    """

    def __init__(self, rng) -> None:  # ``rng`` retained for future extensions
        self.rng = rng

    def evolve(self, world: WorldState) -> WorldState:
        # Preserve existing state if absent – defensive programming.
        att_state: AttentionState = getattr(world, "attention_state", AttentionState())
        graph: ActiveSemanticGraph = world.active_semantic_graph

        # -----------------------------------------------------------------
        # 1️⃣ Determine ordered concepts by activation score.
        # -----------------------------------------------------------------
        sorted_nodes = sorted(
            graph.active_nodes,
            key=lambda n: (-n.activation_score, n.concept_id),
        )
        concept_order: Tuple[str, ...] = tuple(node.concept_id for node in sorted_nodes)

        # -----------------------------------------------------------------
        # 2️⃣ Apply capacity limits.
        # -----------------------------------------------------------------
        capacity = att_state.attention_capacity
        focused = concept_order[:capacity]
        suppressed = concept_order[capacity:]
        load = len(focused)

        # -----------------------------------------------------------------
        # 3️⃣ Detect overload.
        # -----------------------------------------------------------------
        events: List[TimelineEvent] = []
        new_att_state = att_state.with_focus(focused).with_load(load)
        new_att_state = new_att_state.replace(
            suppressed_concepts=suppressed,
        ) if hasattr(new_att_state, "replace") else new_att_state
        # The ``replace`` call is not available – we construct a new instance.
        new_att_state = new_att_state.with_focus(focused).with_load(load)
        # Update suppressed concepts explicitly via ``replace`` using dataclasses.
        from dataclasses import replace as _replace
        new_att_state = _replace(new_att_state, suppressed_concepts=suppressed)

        if load > att_state.overload_threshold and att_state.overload_threshold > 0:
            events.append(TimelineEvent(world.tick, "attentional_overload"))
            # Increment fatigue modestly.
            new_att_state = new_att_state.with_fatigue(min(1.0, att_state.attentional_fatigue + 0.1))
        else:
            # Gradually recover fatigue.
            new_att_state = new_att_state.with_fatigue(max(0.0, att_state.attentional_fatigue - 0.01))

        # -----------------------------------------------------------------
        # 4️⃣ Fixation detection – if any previously‑fixated concept remains focused.
        # -----------------------------------------------------------------
        if any(c in att_state.fixation_targets for c in focused):
            events.append(TimelineEvent(world.tick, "fixation_detected"))

        # -----------------------------------------------------------------
        # 5️⃣ Context‑switch penalty – fire when the focus set changes.
        # -----------------------------------------------------------------
        if set(focused) != set(att_state.focused_concepts):
            events.append(TimelineEvent(world.tick, "context_switch_penalty"))

        # -----------------------------------------------------------------
        # 6️⃣ Assemble new world state.
        # -----------------------------------------------------------------
        new_world = world.with_attention_state(new_att_state)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
