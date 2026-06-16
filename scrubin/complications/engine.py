"""Deterministic complication engine.

Manages activation, progression, escalation, and resolution of complications.
All state updates are performed via ``dataclasses.replace`` and the engine
operates on immutable ``Complication`` instances.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple, List, Dict, Set, Any

from .models import Complication


class ComplicationEngine:
    """Engine that tracks deterministic complication lifecycles.

    * ``trigger`` – step ID that activates the complication.
    * ``resolution`` – step ID that resolves the complication.
    * ``progression_rate`` – severity increase per tick while active.
    * ``recovery_rate`` – severity decrease when an intervention occurs.
    """

    def __init__(self, complications: Tuple[Complication, ...]):
        # Map id -> Complication (immutable templates).
        self._templates: Dict[str, Complication] = {c.id: c for c in complications}
        # Runtime state: id -> Complication (mutable via replace).
        self._active: Dict[str, Complication] = {}

    def _activate(self, comp_id: str) -> None:
        tmpl = self._templates[comp_id]
        active = replace(tmpl, active=True)
        self._active[comp_id] = active

    def _resolve(self, comp_id: str) -> None:
        comp = self._active.pop(comp_id, None)
        if comp:
            resolved = replace(comp, active=False, resolved=True)
            # resolved instance not kept in active dict; returned via events.
            return resolved
        return None

    def _progress(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for cid, comp in list(self._active.items()):
            if comp.progression_rate:
                new_sev = min(1.0, comp.severity + comp.progression_rate)
                comp = replace(comp, severity=new_sev)
                self._active[cid] = comp
                events.append({"type": "ComplicationProgressed", "complication": cid, "severity": new_sev})
        return events

    def update(self, workflow_state: Any, interventions: Tuple[str, ...] = ()) -> Tuple[List[Dict[str, Any]], Tuple[str, ...]]:
        """Update complication lifecycle based on workflow state.

        * ``workflow_state`` – current immutable ``WorkflowState``.
        * ``interventions`` – tuple of complication IDs that received an
          intervention this tick (used to apply ``recovery_rate``).

        Returns a list of deterministic events and the updated tuple of active
        complication IDs.
        """
        events: List[Dict[str, Any]] = []
        # 1. Trigger new complications.
        for comp in self._templates.values():
            if comp.id not in self._active and comp.trigger and comp.trigger in workflow_state.completed_steps:
                self._activate(comp.id)
                events.append({"type": "ComplicationActivated", "complication": comp.id})
        # 2. Apply progression for all active complications.
        events.extend(self._progress())
        # 3. Apply recovery for intervened complications.
        for cid in interventions:
            if cid in self._active:
                comp = self._active[cid]
                if comp.recovery_rate:
                    new_sev = max(0.0, comp.severity - comp.recovery_rate)
                    comp = replace(comp, severity=new_sev)
                    self._active[cid] = comp
                    events.append({"type": "ComplicationRecovered", "complication": cid, "severity": new_sev})
        # 4. Resolve complications whose resolution step has been completed.
        resolved_ids: List[str] = []
        for cid, comp in list(self._active.items()):
            if comp.resolution and comp.resolution in workflow_state.completed_steps:
                resolved = self._resolve(cid)
                resolved_ids.append(cid)
                events.append({"type": "ComplicationResolved", "complication": cid})
        # Return events and ordered active IDs.
        active_ids = tuple(sorted(self._active.keys()))
        return events, active_ids
