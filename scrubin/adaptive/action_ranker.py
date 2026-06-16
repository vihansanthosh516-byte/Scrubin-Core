'''Deterministic action ranking engine.

The ``ActionRanker`` scores actions using a deterministic formula derived from
several risk and priority metrics. No stochastic weighting is applied – the
formula is a simple linear combination with fixed coefficients, guaranteeing
identical ordering across runs.
''' 

from __future__ import annotations

from typing import Tuple, Mapping, Any

from .models import AdaptiveAction


class ActionRanker:
    """Score and deterministically order ``AdaptiveAction`` objects.

    ``rank_actions`` expects a mapping from ``action_id`` to a dictionary of
    metric values. Missing metric entries default to ``0.0``.
    """

    # Fixed deterministic coefficients – chosen to reflect relative importance.
    _WEIGHTS = {
        "mortality_risk": 10.0,
        "physiology_instability": 8.0,
        "executive_priority": 6.0,
        "workflow_delay": 5.0,
        "anatomy_injury": 4.0,
        "contamination": 3.0,
        "perfusion_deficit": 2.0,
        "recovery_urgency": 1.0,
    }

    @staticmethod
    def _score(action: AdaptiveAction, metrics: Mapping[str, float]) -> float:
        """Calculate a deterministic score for a single action.

        Higher scores indicate greater urgency for execution.
        """
        # If no metrics are provided for this action, assign a maximal score so that it sorts after scored actions.
        if not metrics:
            return float('inf')
        total = 0.0
        for metric, weight in ActionRanker._WEIGHTS.items():
            total += weight * float(metrics.get(metric, 0.0))
        # Incorporate the action's intrinsic priority as a tie‑breaker.
        total += action.priority * 0.01
        return total

    def rank_actions(
        self,
        actions: Tuple[AdaptiveAction, ...],
        metrics_by_action: Mapping[str, Mapping[str, float]] = {},
    ) -> Tuple[AdaptiveAction, ...]:
        """Return actions sorted by deterministic score.

        ``metrics_by_action`` maps ``action_id`` → ``{metric_name: value}``. The
        ranking is deterministic because the scoring formula and the secondary
        lexical ``action_id`` tie‑breaker are both fixed.
        """
        # Separate actions with provided metrics (scored) from those without (unsorted).
        scored: list[tuple[float, str, AdaptiveAction]] = []
        unsorted: list[AdaptiveAction] = []
        for act in actions:
            metrics = metrics_by_action.get(act.action_id, {})
            if metrics:
                score = self._score(act, metrics)
                scored.append((score, act.action_id, act))
            else:
                unsorted.append(act)
        # Sort scored actions by ascending score, then lexical action_id.
        scored.sort(key=lambda item: (item[0], item[1]))
        # Combine scored actions (sorted) with unsorted actions preserving original order.
        ordered = [item[2] for item in scored] + unsorted
        return tuple(ordered)
