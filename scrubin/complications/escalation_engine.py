"""Deterministic escalation engine.
+
+The engine determines whether active complications should be escalated based on
+immutable snapshots of physiology, anatomy, OR team, and workflow state.  The
+implementation avoids any randomness – decisions are derived solely from the
+provided dictionaries.
+"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple, List, Mapping, Any

from .models import Complication, ComplicationState, ComplicationEvent


class EscalationEngine:
    """Stateless escalation logic.
+
+    The deterministic rule set (simple but illustrative):
+    * If ``physiology['stress']`` > ``thresholds['stress']`` *or*
+      ``anatomy['damage']`` > ``thresholds['damage']`` then any active
+      complication in ``Active`` stage moves to ``Escalating``.
+    * If the OR team is understaffed (``or_team['staff_available']`` < 1) the
+      escalation also applies.
+    * Otherwise no change.
+    The function returns an updated ``ComplicationState`` and a collection of
+    ``EscalationEvent`` objects.
+    """

    @staticmethod
    def evaluate(
        state: ComplicationState,
        physiology: Mapping[str, Any],
        anatomy: Mapping[str, Any],
        or_team: Mapping[str, Any],
        workflow: Mapping[str, Any],
        thresholds: Mapping[str, int] | None = None,
    ) -> Tuple[ComplicationState, Tuple[ComplicationEvent, ...]]:
        if thresholds is None:
            thresholds = {"stress": 5, "damage": 3}

        events: List[ComplicationEvent] = []
        new_active: List[Complication] = []
        for comp in state.active_complications:
            should_escalate = False
            if physiology.get("stress", 0) > thresholds["stress"]:
                should_escalate = True
            if anatomy.get("damage", 0) > thresholds["damage"]:
                should_escalate = True
            if or_team.get("staff_available", 1) < 1:
                should_escalate = True
            # Workflow flags could also trigger escalation; example deterministic check
            if workflow.get("emergency", False):
                should_escalate = True

            if should_escalate and comp.progression_stage == "Active":
                updated = replace(comp, progression_stage="Escalating", last_update_tick=comp.last_update_tick)
                new_active.append(updated)
                ev = ComplicationEvent(
                    tick=comp.last_update_tick,
                    event_type="escalated",
                    complication_id=comp.deterministic_id,
                    details={"reason": "deterministic_rules"},
                )
                events.append(ev)
            else:
                new_active.append(comp)

        # Preserve deterministic ordering by sorting after updates
        new_active.sort(key=lambda c: c.deterministic_id)
        # If no changes occurred (no events and new_active equals original), return original state.
        if not events and tuple(new_active) == state.active_complications:
            return state, tuple()
        new_state = state.with_updates(remove_active_ids=tuple(c.deterministic_id for c in state.active_complications), add_active=tuple(new_active))
        return new_state, tuple(events)
