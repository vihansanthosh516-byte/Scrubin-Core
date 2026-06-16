"""Deterministic recovery planner for complications.
+
+The planner inspects a :class:`ComplicationState` and produces a
+``RecoveryPlan`` that lists recommended state transitions for each active
+complication.  All logic is pure – it relies only on the immutable input state
+and returns new objects without side‑effects.
+"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, List

from .models import Complication, ComplicationState, ComplicationEvent


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    """Single deterministic action for a complication.
+
+    ``new_stage`` is the target progression stage, and ``severity`` is the
+    adjusted severity after recovery actions.
+    """

    complication_id: int
    new_stage: str
    severity: int
    note: str = ""


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Immutable collection of recovery actions.
+
+    ``actions`` are stored as a sorted tuple to guarantee deterministic order.
+    """

    actions: Tuple[RecoveryAction, ...] = ()

    def with_added(self, action: RecoveryAction) -> "RecoveryPlan":
        new_actions = list(self.actions) + [action]
        new_actions.sort(key=lambda a: a.complication_id)
        return replace(self, actions=tuple(new_actions))


class RecoveryPlanner:
    """Pure planner that evaluates a ``ComplicationState``.
+
+    The deterministic policy is simple:
+    * If a complication is in ``Critical`` stage, propose moving to ``Recovering``
+      and reduce severity by 1 (minimum 1).
+    * If a complication is in ``Escalating`` stage, propose moving to ``Critical``
+      (severity unchanged).
+    * Otherwise, no action.
+    """

    @staticmethod
    def evaluate(state: ComplicationState) -> Tuple[RecoveryPlan, Tuple[ComplicationEvent, ...]]:
        plan = RecoveryPlan()
        events: List[ComplicationEvent] = []
        for comp in state.active_complications:
            if comp.progression_stage == "Critical":
                new_severity = max(1, comp.severity - 1)
                action = RecoveryAction(
                    complication_id=comp.deterministic_id,
                    new_stage="Recovering",
                    severity=new_severity,
                    note="auto‑recovery from critical",
                )
                plan = plan.with_added(action)
                ev = ComplicationEvent(
                    tick=comp.last_update_tick,
                    event_type="recovery_proposed",
                    complication_id=comp.deterministic_id,
                    details={"to": "Recovering", "severity": new_severity},
                )
                events.append(ev)
            elif comp.progression_stage == "Escalating":
                action = RecoveryAction(
                    complication_id=comp.deterministic_id,
                    new_stage="Critical",
                    severity=comp.severity,
                    note="escalation to critical",
                )
                plan = plan.with_added(action)
                ev = ComplicationEvent(
                    tick=comp.last_update_tick,
                    event_type="recovery_proposed",
                    complication_id=comp.deterministic_id,
                    details={"to": "Critical"},
                )
                events.append(ev)
        return plan, tuple(events)
