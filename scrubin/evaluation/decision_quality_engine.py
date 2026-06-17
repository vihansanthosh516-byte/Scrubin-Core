"""DecisionQualityEngine – evaluates the quality of executive decisions.
All calculations are deterministic and based only on input lengths and simple
numeric fields.  No randomness or external data is used.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import DecisionQualityReport


class DecisionQualityEngine:
    @staticmethod
    def evaluate(
        goals: Tuple[Any, ...] = (),
        decisions: Tuple[Any, ...] = (),
        forecasts: Tuple[Any, ...] = (),
        risks: Tuple[Any, ...] = (),
    ) -> DecisionQualityReport:
        """Compute deterministic quality metrics.

        * ``optimality`` – ratio of decisions to goals.
        * ``efficiency`` – forecasts per decision.
        * ``unnecessary_actions`` – excess decisions over goals.
        * ``delayed_actions`` – count of decisions where ``delayed`` attribute is True.
        * ``confidence_alignment`` – average ``confidence`` attribute of decisions.
        """
        goal_cnt = len(goals)
        decision_cnt = len(decisions)
        optimality = decision_cnt / goal_cnt if goal_cnt else 0.0
        efficiency = len(forecasts) / decision_cnt if decision_cnt else 0.0
        unnecessary_actions = max(0, decision_cnt - goal_cnt)
        delayed_actions = sum(1 for d in decisions if getattr(d, "delayed", False))
        confidence_sum = sum(getattr(d, "confidence", 0.0) for d in decisions)
        confidence_alignment = confidence_sum / decision_cnt if decision_cnt else 0.0

        return DecisionQualityReport(
            optimality=optimality,
            efficiency=efficiency,
            unnecessary_actions=unnecessary_actions,
            delayed_actions=delayed_actions,
            confidence_alignment=confidence_alignment,
        )
