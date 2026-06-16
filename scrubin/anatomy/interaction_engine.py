"""Deterministic interaction engine for anatomy.

The engine holds an immutable ``AnatomyGraph`` and a tuple of ``TissueState``
objects.  Interactions such as ``cut`` or ``retract`` produce a new engine
instance, a list of deterministic events and an optional physiology delta that
can be applied to the overall physiology engine.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple, List, Dict

from .graph import AnatomyGraph
from .state import TissueState
from .models import AnatomicalStructure, Vessel, Organ


class InteractionEngine:
    """Immutable engine that applies deterministic interactions to anatomy.

    ``graph`` – immutable ``AnatomyGraph``.
    ``tissue_states`` – tuple of ``TissueState`` objects, one per structure.
    """

    def __init__(self, graph: AnatomyGraph, tissue_states: Tuple[TissueState, ...] = None):
        self.graph = graph
        if tissue_states is None:
            # Initialise default tissue state for every structure.
            self.tissue_states = tuple(TissueState(structure_id=s.id) for s in graph._structures.values())
        else:
            self.tissue_states = tissue_states

    # ---------------------------------------------------------------------
    # Helper to fetch the current tissue state for a given structure.
    # ---------------------------------------------------------------------
    def _state_for(self, structure_id: str) -> TissueState:
        for ts in self.tissue_states:
            if ts.structure_id == structure_id:
                return ts
        # Should not happen – fallback to a default state.
        return TissueState(structure_id=structure_id)

    # ---------------------------------------------------------------------
    # Core interaction method.
    # ---------------------------------------------------------------------
    def apply_interaction(self, interaction: str, target_id: str, instrument: str) -> Tuple["InteractionEngine", List[Dict], Dict]:
        """Apply ``interaction`` to ``target_id`` using ``instrument``.

        Returns a new ``InteractionEngine`` with updated ``tissue_states``, a list
        of deterministic event dictionaries, and an optional physiology delta.
        """
        events: List[Dict] = []
        phys_delta: Dict[str, float] = {}

        # Retrieve structure and current state.
        struct = self.graph.get(target_id)
        current_state = self._state_for(target_id)

        # Simple exposure check – many interactions require the structure to be visible.
        requires_exposed = interaction in ("cut", "dissect", "divide", "cauterize")
        if requires_exposed and not struct.visible:
            events.append({"type": "Injury", "structure": target_id, "injury_type": f"{interaction}_unexposed"})
            # No state change – return unchanged engine.
            return self, events, phys_delta

        # Determine new tissue state based on interaction.
        new_state = current_state
        if interaction == "cut":
            new_state = replace(current_state, dissected=True, intact=False)
        elif interaction == "retract":
            new_state = replace(current_state, retracted=True)
        elif interaction == "grasp":
            # No persistent flag for grasp – only an event.
            pass
        elif interaction == "dissect":
            new_state = replace(current_state, dissected=True)
        elif interaction == "cauterize":
            new_state = replace(current_state, cauterized=True)
        elif interaction == "staple":
            new_state = replace(current_state, ligated=True)
        elif interaction == "clip":
            new_state = replace(current_state, clipped=True)
        elif interaction == "suction":
            # No state change.
            pass
        elif interaction == "irrigate":
            # No state change.
            pass
        elif interaction == "divide":
            new_state = replace(current_state, divided=True, intact=False)
        else:
            # Unknown interaction – no effect.
            pass

        # Record interaction event if a state change occurred.
        if new_state != current_state:
            events.append({
                "type": f"Interaction{interaction.title()}",
                "structure": target_id,
                "instrument": instrument,
            })
            # Update tissue_states tuple immutably.
            new_states = list(self.tissue_states)
            # Find index of the existing state.
            idx = next(i for i, ts in enumerate(new_states) if ts.structure_id == target_id)
            new_states[idx] = new_state
        else:
            new_states = list(self.tissue_states)

        # Simple deterministic physiology coupling.
        # Vessel cut/divide -> blood volume loss.
        if interaction in ("cut", "divide") and isinstance(struct, Vessel):
            phys_delta["BloodVolume"] = -200.0
        # Organ cauterization -> oxygenation drop.
        if interaction == "cauterize" and isinstance(struct, Organ):
            phys_delta["SpO2"] = -5.0

        new_engine = InteractionEngine(self.graph, tuple(new_states))
        return new_engine, events, phys_delta
