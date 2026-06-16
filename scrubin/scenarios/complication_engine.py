"""Deterministic complication engine.

Tracks activation and resolution of complications based on workflow progress.
No randomness – triggers and resolutions are defined by explicit step IDs in the
scenario's ``Complication`` definitions.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple, List, Dict, Set, Any

from .models import Complication, ProcedureScenario


class ComplicationEngine:
    """Manages deterministic complication lifecycle.

    * ``trigger`` – a step ID that, when completed, activates the complication.
    * ``resolution`` – a step ID that resolves the complication when completed.
    The engine updates the set of active complications and emits events.
    """

    def __init__(self, complications: Tuple[Complication, ...]):
        self._comp_map: Dict[str, Complication] = {c.id: c for c in complications}
        # active complications are tracked in the workflow state.

    def update(self, workflow_state: Any) -> Tuple[List[Dict], Tuple[str, ...]]:
        """Process triggers/resolutions based on the current workflow state.

        Returns a list of events and the updated tuple of active complication IDs.
        """
        events: List[Dict] = []
        active: Set[str] = set(workflow_state.active_complications)
        # Trigger new complications.
        for comp in self._comp_map.values():
            if comp.id not in active and comp.trigger and comp.trigger in workflow_state.completed_steps:
                active.add(comp.id)
                events.append({"type": "ComplicationTriggered", "complication": comp.id})
        # Resolve complications.
        resolved: List[str] = []
        for cid in list(active):
            comp = self._comp_map.get(cid)
            if comp and comp.resolution and comp.resolution in workflow_state.completed_steps:
                active.remove(cid)
                resolved.append(cid)
                events.append({"type": "ComplicationResolved", "complication": cid})
        # Return events and the new active tuple.
        return events, tuple(active)
