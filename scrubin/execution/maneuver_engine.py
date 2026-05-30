from __future__ import annotations

"""Deterministic maneuver execution engine.

Executes low‑level surgical maneuvers derived from the ``IntentGraph``. The
engine updates the ``TechnicalExecutionState`` and emits timeline events that
reflect procedural quality.
"""

from typing import List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.ontology.intent_graph import IntentGraph
from scrubin.execution.state import TechnicalExecutionState
from scrubin.ontology.attention_state import AttentionState
from scrubin.ontology.overload_state import OverloadState
from scrubin.execution.skill_model import OperatorSkillProfile


class ManeuverExecutionEngine:
    """Execute maneuvers deterministically, degrading quality under load.

    The stub selects the next pending intent (by deterministic ordering) and
    treats its ``intent_id`` as the maneuver identifier. Success is based on a
    deterministic rule that combines attention overload and operator fatigue.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def execute(self, world: WorldState) -> WorldState:
        intent_graph: IntentGraph = getattr(world, "intent_graph", IntentGraph())
        pending = intent_graph.pending_intents()
        tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
        att: AttentionState = getattr(world, "attention_state", AttentionState())
        overload: OverloadState = getattr(world, "overload_state", OverloadState())
        skill: OperatorSkillProfile = getattr(world, "operator_skill_profile", OperatorSkillProfile())

        events: List[TimelineEvent] = []

        if not pending:
            # No maneuvers to execute.
            return world

        # Deterministically pick the first pending intent.
        maneuver = pending[0].intent_id
        tech = tech.with_current_maneuver(maneuver)
        tech = tech.add_execution_history(world.tick, maneuver)

        # Deterministic success rule: if overload or low skill -> failure.
        overload_factor = overload.overload_level
        skill_factor = (skill.dexterity + skill.steadiness) / 2.0
        success_probability = max(0.0, min(1.0, skill_factor - overload_factor))
        # No randomness – success if probability >= 0.5, else failure.
        if success_probability >= 0.5:
            tech = tech.add_successful_maneuver(maneuver)
            events.append(TimelineEvent(world.tick, f"maneuver_success:{maneuver}"))
        else:
            tech = tech.add_failed_maneuver(maneuver)
            events.append(TimelineEvent(world.tick, f"maneuver_failure:{maneuver}"))
            # Increment risk and micro‑error accumulation.
            tech = tech.with_current_risk_level(min(1.0, tech.current_risk_level + 0.1))
            tech = tech.with_micro_error_accumulation(tech.micro_error_accumulation + 0.05)

        # Update fatigue based on effort.
        fatigue_increment = 0.01 * (1.0 - skill.fatigue_resistance)
        tech = tech.with_cumulative_technical_fatigue(min(1.0, tech.cumulative_technical_fatigue + fatigue_increment))

        new_world = world.with_technical_execution_state(tech)
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
