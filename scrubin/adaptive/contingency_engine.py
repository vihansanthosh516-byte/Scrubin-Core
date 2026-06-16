'''Deterministic contingency generation.

The ``ContingencyEngine`` creates immutable ``ContingencyPlan`` objects that
represent fallback action sequences for well‑defined trigger conditions. The
engine does not analyse the input plan – it merely provides a static mapping of
trigger identifiers to symbolic action sequences as described in the
specification.
''' 

from __future__ import annotations

from typing import Tuple, Iterable

from .models import AdaptiveAction, ContingencyPlan


class ContingencyEngine:
    """Generate deterministic contingency plans for a given adaptive plan.

    The implementation is intentionally simple – it returns a fixed set of
    contingency plans for three canonical trigger conditions. The actions are
    deterministic ``AdaptiveAction`` instances with increasing priority values.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def _make_action(action_id: str, description: str, priority: int) -> AdaptiveAction:
        return AdaptiveAction(action_id=action_id, description=description, priority=priority)

    def generate_contingencies(
        self,
        adaptive_plan: Any = None,
        triggers: Iterable[str] = ("hemorrhage_worsens", "hypoxia_worsens", "instability_worsens"),
    ) -> Tuple[ContingencyPlan, ...]:
        """Return a tuple of ``ContingencyPlan`` objects for the supplied triggers.

        ``adaptive_plan`` is accepted for API compatibility but is not required
        for the deterministic placeholder implementation.
        """
        contingency_list: list[ContingencyPlan] = []

        for trigger in triggers:
            if trigger == "hemorrhage_worsens":
                steps = (
                    self._make_action("pack_hemorrhage", "pack", 0),
                    self._make_action("suction_hemorrhage", "suction", 1),
                    self._make_action("clamp_hemorrhage", "clamp", 2),
                    self._make_action("call_assistance_hemorrhage", "call assistance", 3),
                )
            elif trigger == "hypoxia_worsens":
                steps = (
                    self._make_action("increase_ventilation", "ventilate", 0),
                    self._make_action("pause_procedure", "pause", 1),
                    self._make_action("stabilize_oxygen", "stabilize", 2),
                )
            elif trigger == "instability_worsens":
                steps = (
                    self._make_action("terminate_procedure", "terminate procedure", 0),
                )
            else:
                # Unknown triggers produce an empty contingency.
                steps = tuple()
            contingency = ContingencyPlan(trigger_condition=trigger, steps=steps)
            contingency_list.append(contingency)

        return tuple(contingency_list)
