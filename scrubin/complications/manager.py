"""Deterministic manager for complications.
+
+All operations are pure – they accept a :class:`ComplicationState` and return a
+new instance together with any produced :class:`ComplicationEvent`s.  The
+manager does not maintain global mutable state, which makes replay and testing
+deterministic.
+"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple

from .models import Complication, ComplicationEvent, ComplicationState


class ComplicationManager:
    """Stateless helper class providing lifecycle operations.
+
+    The class only groups related functions; it does not store mutable state.
+    """

    # Lifecycle stages in order – useful for deterministic transitions.
    _STAGES = ("Inactive", "Active", "Escalating", "Critical", "Recovering", "Resolved")

    @staticmethod
    def activate(state: ComplicationState, comp: Complication, tick: int) -> Tuple[ComplicationState, ComplicationEvent]:
        """Activate a complication.
+
+        Returns a new state with ``comp`` added to ``active_complications`` and an
+        ``"activated"`` event.  ``comp`` is expected to have ``active=False``.
+        """

        # If already active, return existing state unchanged (hash remains stable)
        already_active = any(c.deterministic_id == comp.deterministic_id for c in state.active_complications)
        if already_active:
            event = ComplicationEvent(tick=tick, event_type="activated", complication_id=comp.deterministic_id)
            return state, event
        new_comp = replace(comp, active=True, activation_tick=tick, last_update_tick=tick, progression_stage="Active")
        new_state = state.with_updates(add_active=(new_comp,))
        event = ComplicationEvent(tick=tick, event_type="activated", complication_id=new_comp.deterministic_id)
        return new_state, event

    @staticmethod
    def update(state: ComplicationState, comp_id: int, tick: int, *, new_stage: str | None = None, severity: int | None = None) -> Tuple[ComplicationState, ComplicationEvent]:
        """Update an existing active complication.
+
+        ``new_stage`` must be one of the predefined stages; if omitted the stage
+        remains unchanged.  ``severity`` may be adjusted.
+        """

        # Find the complication
        comp = next(c for c in state.active_complications if c.deterministic_id == comp_id)
        updated = comp.advance_stage(new_stage or comp.progression_stage, tick, severity)
        # Replace in state
        new_state = state.with_updates(remove_active_ids=(comp_id,), add_active=(updated,))
        event = ComplicationEvent(tick=tick, event_type="updated", complication_id=comp_id, details={"stage": updated.progression_stage, "severity": updated.severity})
        return new_state, event

    @staticmethod
    def resolve(state: ComplicationState, comp_id: int, tick: int) -> Tuple[ComplicationState, ComplicationEvent]:
        """Mark a complication as resolved.
+        """

        comp = next(c for c in state.active_complications if c.deterministic_id == comp_id)
        resolved = comp.resolve(tick)
        new_state = state.with_updates(remove_active_ids=(comp_id,), add_resolved=(resolved,))
        event = ComplicationEvent(tick=tick, event_type="resolved", complication_id=comp_id)
        return new_state, event

    @staticmethod
    def remove(state: ComplicationState, comp_id: int) -> ComplicationState:
        """Remove a complication entirely (used for cleanup)."""

        return state.with_updates(remove_active_ids=(comp_id,))
