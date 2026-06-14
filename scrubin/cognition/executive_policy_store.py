"""Append‑only deterministic store for ``ExecutivePolicyDecision`` objects.

Provides O(1) lookup, deterministic ordering, deterministic merge, and query
capabilities. No deletion, immutable entries.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .executive_policy_decision import ExecutivePolicyDecision, deterministic_executive_policy_decision_hash


class ExecutivePolicyStore:
    """Deterministic, append‑only store for executive policy decisions.

    * ``_decisions`` – list preserving insertion order.
    * ``_index`` – maps decision IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._decisions: List[ExecutivePolicyDecision] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate decisions
    # ---------------------------------------------------------------------
    def add_or_update(self, decision: ExecutivePolicyDecision) -> None:
        """Append a new decision or merge with an existing one.

        Merge semantics (deterministic):
            * Union of ``rejected_strategy_ids``, ``supporting_strategy_selection_ids``,
              ``supporting_policy_profile_ids``, ``supporting_adaptation_profile_ids``,
              ``supporting_optimization_ids``, ``supporting_signal_ids`` (sorted).
            * Keep higher ``arbitration_score``.
            * Keep higher ``confidence``.
            * Update ``first_seen_tick`` to min, ``last_seen_tick`` to max.
        """
        if decision.id in self._index:
            idx = self._index[decision.id]
            prior = self._decisions[idx]
            new_rejected = tuple(sorted(set(prior.rejected_strategy_ids) | set(decision.rejected_strategy_ids)))
            new_sel = tuple(sorted(set(prior.supporting_strategy_selection_ids) | set(decision.supporting_strategy_selection_ids)))
            new_policy = tuple(sorted(set(prior.supporting_policy_profile_ids) | set(decision.supporting_policy_profile_ids)))
            new_adapt = tuple(sorted(set(prior.supporting_adaptation_profile_ids) | set(decision.supporting_adaptation_profile_ids)))
            new_opt = tuple(sorted(set(prior.supporting_optimization_ids) | set(decision.supporting_optimization_ids)))
            new_sig = tuple(sorted(set(prior.supporting_signal_ids) | set(decision.supporting_signal_ids)))
            # Keep higher scores
            arb_score = max(prior.arbitration_score, decision.arbitration_score)
            conf = max(prior.confidence, decision.confidence)
            merged = ExecutivePolicyDecision(
                id=prior.id,
                goal_id=prior.goal_id,
                selected_strategy_id=prior.selected_strategy_id,  # stays the same
                arbitration_score=arb_score,
                confidence=conf,
                rejected_strategy_ids=new_rejected,
                supporting_strategy_selection_ids=new_sel,
                supporting_policy_profile_ids=new_policy,
                supporting_adaptation_profile_ids=new_adapt,
                supporting_optimization_ids=new_opt,
                supporting_signal_ids=new_sig,
                first_seen_tick=min(prior.first_seen_tick, decision.first_seen_tick),
                last_seen_tick=max(prior.last_seen_tick, decision.last_seen_tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_executive_policy_decision_hash(merged))
            self._decisions[idx] = merged
        else:
            self._decisions.append(decision)
            self._index[decision.id] = len(self._decisions) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def decisions(self) -> Tuple[ExecutivePolicyDecision, ...]:
        """Immutable view of all stored decisions in insertion order."""
        return tuple(self._decisions)

    def query(self, goal_id: Optional[str] = None) -> Tuple[ExecutivePolicyDecision, ...]:
        """Return decisions matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering.
        Result preserves deterministic insertion order.
        """
        result: List[ExecutivePolicyDecision] = []
        for d in self._decisions:
            if goal_id is not None and d.goal_id != goal_id:
                continue
            result.append(d)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def decision_count(self) -> int:
        return len(self._decisions)

    def mean_score(self) -> float:
        if not self._decisions:
            return 0.0
        return sum(d.arbitration_score for d in self._decisions) / len(self._decisions)

    def mean_confidence(self) -> float:
        if not self._decisions:
            return 0.0
        return sum(d.confidence for d in self._decisions) / len(self._decisions)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_score, mean_confidence)``.
        """
        return (
            self.decision_count(),
            self.mean_score(),
            self.mean_confidence(),
        )
