"""Procedural Phase Engine – deterministic, constraint‑driven phase management.

The engine owns the authoritative logic for advancing, failing, or escalating a
procedure phase based on the immutable :class:`scrubin.world.state.WorldState`.
All side‑effects are modelled as new ``WorldState`` instances; no mutation is
performed in‑place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from scrubin.world.state import WorldState, TimelineEvent
from .procedure import ProcedurePhase
from .random import SimulationRNG


@dataclass(frozen=True)
class ProceduralPhaseEngine:
    """Core engine that evaluates and transitions procedural phases.

    Parameters
    ----------
    phases: Dict[str, ProcedurePhase]
        Mapping of phase identifiers to their declarative definitions.
    """

    phases: Dict[str, ProcedurePhase]

    # ---------------------------------------------------------------------
    # Public API – deterministic evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, world: WorldState, rng: SimulationRNG) -> WorldState:
        """Evaluate the current phase and return an updated ``WorldState``.

        The method performs three checks in order:
        1️⃣ ``should_fail`` – if true, the phase is marked failed and a
           ``phase_failed`` timeline event is emitted.
        2️⃣ ``can_complete`` – if true, the phase is completed, a ``phase_completed``
           event is recorded, and the engine attempts to transition to the next
           phase (if ``can_enter`` permits it).
        3️⃣ If neither condition holds, the world is returned unchanged.
        """
        current_id = world.procedure.current_phase
        if not current_id:
            # No active phase – nothing to evaluate.
            return world
        phase = self.phases.get(current_id)
        if phase is None:
            # Unknown phase – raise a clear error.
            raise ValueError(f"ProceduralPhaseEngine: unknown phase '{current_id}'")

        # 1️⃣ Failure check – highest priority.
        if phase.should_fail(world):
            event = TimelineEvent(tick=world.tick, description=f"phase_failed:{current_id}")
            return world.append_timeline(event)

        # 2️⃣ Completion check.
        if phase.can_complete(world):
            # Record completion event first.
            completed_event = TimelineEvent(tick=world.tick, description=f"phase_completed:{current_id}")
            new_world = world.append_timeline(completed_event)

            # Determine the next phase – we look for a metadata key ``next_phase``.
            # If not present, we stay in the current phase (no auto‑advance).
            next_phase_id: Optional[str] = getattr(phase, "metadata", {}).get("next_phase")
            if next_phase_id and next_phase_id in self.phases:
                next_phase = self.phases[next_phase_id]
                # Verify entry predicates for the next phase.
                if next_phase.can_enter(new_world):
                    # Update the procedure state.
                    proc_state = new_world.procedure.with_phase(next_phase_id)
                    new_world = new_world.with_procedure(proc_state)
                    # Emit entry event.
                    enter_event = TimelineEvent(tick=new_world.tick, description=f"phase_entered:{next_phase_id}")
                    new_world = new_world.append_timeline(enter_event)
                else:
                    # Entry conditions not met – stay in current phase.
                    pass
            return new_world

        # 3️⃣ No state change – return world unchanged.
        return world
