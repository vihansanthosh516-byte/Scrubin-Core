from __future__ import annotations

"""Immutable executive attention model.

The design mirrors the rest of the ontology – fields are immutable and updates
are performed through ``with_*`` helpers that return a new instance via
``replace``.  All collections are stored as ``tuple`` to guarantee deterministic
ordering.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class AttentionState:
    """State governing the allocation of limited cognitive attention.

    The fields correspond to the specification in the Phase O.5 design
    document.  Default values are chosen to be neutral (empty tuples, zeros) so
    that the engine can safely operate even when no explicit configuration is
    supplied.
    """

    focused_concepts: Tuple[str, ...] = field(default_factory=tuple)
    suppressed_concepts: Tuple[str, ...] = field(default_factory=tuple)
    active_channels: Tuple[str, ...] = field(default_factory=tuple)
    attention_capacity: int = 5
    overload_threshold: int = 10
    current_load: int = 0
    fixation_targets: Tuple[str, ...] = field(default_factory=tuple)
    interruption_queue: Tuple[str, ...] = field(default_factory=tuple)
    task_switch_penalty: float = 0.0
    salience_weights: Tuple[float, ...] = field(default_factory=tuple)
    executive_mode: str = "normal"
    awareness_decay: float = 0.0
    cognitive_bandwidth: float = 1.0
    sustained_focus_ticks: int = 0
    attentional_fatigue: float = 0.0
    priority_snapshot: Tuple[int, ...] = field(default_factory=tuple)
    uncertainty_pressure: float = 0.0
    semantic_noise: float = 0.0

    # ---------------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable instance.
    # ---------------------------------------------------------------------
    def with_focus(self, focused: Tuple[str, ...]) -> "AttentionState":
        return replace(self, focused_concepts=focused)

    def with_load(self, load: int) -> "AttentionState":
        return replace(self, current_load=load)

    def with_fixation(self, fixation: Tuple[str, ...]) -> "AttentionState":
        return replace(self, fixation_targets=fixation)

    def with_capacity(self, capacity: int, overload_thresh: int | None = None) -> "AttentionState":
        new_state = replace(self, attention_capacity=capacity)
        if overload_thresh is not None:
            new_state = replace(new_state, overload_threshold=overload_thresh)
        return new_state

    def with_priority_snapshot(self, snapshot: Tuple[int, ...]) -> "AttentionState":
        return replace(self, priority_snapshot=snapshot)

    def with_fatigue(self, fatigue: float) -> "AttentionState":
        # Clamp to [0.0, 1.0] for safety.
        fatigue = max(0.0, min(1.0, fatigue))
        return replace(self, attentional_fatigue=fatigue)
