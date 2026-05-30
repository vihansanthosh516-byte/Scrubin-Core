from __future__ import annotations

"""Deterministic instrument–tissue interaction engine.

The engine evaluates the compatibility of the currently selected instrument with
the target tissue and emits timeline events for any deterministic hazards.
"""

from typing import List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.execution.skill_model import OperatorSkillProfile


class InstrumentInteractionEngine:
    """Evaluate instrument‑tissue interactions and apply deterministic effects.

    The implementation is intentionally lightweight – it calculates a simple
    deterministic ``stress`` metric using force, tissue fragility (derived from
    exposure quality), operator fatigue and attention overload.
    """

    def __init__(self, rng) -> None:
        self.rng = rng  # retained for future tie‑breaking if needed

    def interact(self, world: WorldState) -> WorldState:
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        att: AttentionState = getattr(world, "attention_state", AttentionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        skill: OperatorSkillProfile = getattr(world, "operator_skill_profile", OperatorSkillProfile())

        events: List[TimelineEvent] = []

        # Simplified deterministic stress calculation.
        stress = (
            tech.force_application * (1.0 - tech.exposure_quality) * (1.0 - skill.fatigue_resistance)
        )

        # Thresholds for deterministic events.
        if stress > 0.5:
            events.append(TimelineEvent(world.tick, "unsafe_force_detected"))
        if tech.visualization_quality < 0.3:
            events.append(TimelineEvent(world.tick, "visualization_compromised"))
        if att.current_load > att.overload_threshold:
            events.append(TimelineEvent(world.tick, "tissue_traction_risk"))
        if overload.overload_level > 0.6:
            events.append(TimelineEvent(world.tick, "microvascular_injury"))

        # Update technical fatigue deterministically.
        new_fatigue = min(1.0, tech.cumulative_technical_fatigue + 0.02 * (stress > 0.5))
        tech = tech.with_cumulative_technical_fatigue(new_fatigue)

        new_world = world.with_technical_execution_state(tech)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
