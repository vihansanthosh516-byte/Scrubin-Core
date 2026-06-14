"""Append‑only deterministic store for ``ExecutiveEvaluation`` objects.

Provides O(1) lookup by evaluation ID and deterministic query ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple, Optional, Dict

from .executive_evaluation import ExecutiveEvaluation, deterministic_executive_evaluation_hash


class ExecutiveEvaluationStore:
    """Deterministic, append‑only store for executive evaluations.

    * ``_evaluations`` – list preserving insertion order.
    * ``_index`` – maps evaluation IDs to list indices for O(1) lookup.
    """

    def __init__(self) -> None:
        self._evaluations: List[ExecutiveEvaluation] = []
        self._index: Dict[str, int] = {}

    # ---------------------------------------------------------------------
    # Core mutation – deterministic merging of duplicate evaluations
    # ---------------------------------------------------------------------
    def add_or_update(self, evaluation: ExecutiveEvaluation) -> None:
        """Append a new evaluation or merge with an existing one.

        On duplicate IDs, supporting IDs are unioned, the higher evaluation_score
        is retained, and the later tick is kept. The merged object receives a new
        deterministic replay hash.
        """
        if evaluation.id in self._index:
            idx = self._index[evaluation.id]
            prior = self._evaluations[idx]
            # Merge supporting IDs (union)
            new_episodes = tuple(sorted(set(prior.supporting_episode_ids) | set(evaluation.supporting_episode_ids)))
            new_facts = tuple(sorted(set(prior.supporting_fact_ids) | set(evaluation.supporting_fact_ids)))
            new_beliefs = tuple(sorted(set(prior.supporting_belief_ids) | set(evaluation.supporting_belief_ids)))
            new_reflections = tuple(sorted(set(prior.supporting_reflection_ids) | set(evaluation.supporting_reflection_ids)))
            new_counterfactuals = tuple(sorted(set(prior.supporting_counterfactual_ids) | set(evaluation.supporting_counterfactual_ids)))
            # Choose higher scores
            eval_score = max(prior.evaluation_score, evaluation.evaluation_score)
            conf_score = max(prior.confidence_score, evaluation.confidence_score)
            outcome_score = max(prior.outcome_score, evaluation.outcome_score)
            merged = ExecutiveEvaluation(
                id=prior.id,
                goal_id=prior.goal_id,
                strategy_id=prior.strategy_id,
                selection_id=prior.selection_id,
                evaluation_score=eval_score,
                outcome_score=outcome_score,
                confidence_score=conf_score,
                supporting_episode_ids=new_episodes,
                supporting_fact_ids=new_facts,
                supporting_belief_ids=new_beliefs,
                supporting_reflection_ids=new_reflections,
                supporting_counterfactual_ids=new_counterfactuals,
                tick=max(prior.tick, evaluation.tick),
                replay_hash="",
            )
            merged = replace(merged, replay_hash=deterministic_executive_evaluation_hash(merged))
            self._evaluations[idx] = merged
        else:
            self._evaluations.append(evaluation)
            self._index[evaluation.id] = len(self._evaluations) - 1

    # ---------------------------------------------------------------------
    # Query API – deterministic ordering, O(1) exact matches
    # ---------------------------------------------------------------------
    @property
    def evaluations(self) -> Tuple[ExecutiveEvaluation, ...]:
        """Immutable view of all stored evaluations in insertion order."""
        return tuple(self._evaluations)

    def query(
        self,
        goal_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> Tuple[ExecutiveEvaluation, ...]:
        """Return evaluations matching the supplied criteria.

        Parameters are optional – ``None`` means no filtering on that field.
        The result preserves deterministic insertion order.
        """
        result: List[ExecutiveEvaluation] = []
        for ev in self._evaluations:
            if goal_id is not None and ev.goal_id != goal_id:
                continue
            if strategy_id is not None and ev.strategy_id != strategy_id:
                continue
            if min_score is not None and ev.evaluation_score < min_score:
                continue
            result.append(ev)
        return tuple(result)

    # ---------------------------------------------------------------------
    # Statistics helpers
    # ---------------------------------------------------------------------
    def evaluation_count(self) -> int:
        return len(self._evaluations)

    def mean_evaluation_score(self) -> float:
        if not self._evaluations:
            return 0.0
        return sum(ev.evaluation_score for ev in self._evaluations) / len(self._evaluations)

    def mean_confidence_score(self) -> float:
        if not self._evaluations:
            return 0.0
        return sum(ev.confidence_score for ev in self._evaluations) / len(self._evaluations)

    def summary(self) -> Tuple[int, float, float]:
        """Return ``(count, mean_evaluation_score, mean_confidence_score)``.
        """
        return (
            self.evaluation_count(),
            self.mean_evaluation_score(),
            self.mean_confidence_score(),
        )
