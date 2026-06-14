"""Deterministic executive ranking based on bias‑aware plan candidates.

Produces a mapping from each executive goal to the chosen strategy ID according
to a deterministic ordering that incorporates the bias‑aware final score and
tie‑breaking rules.
"""

from __future__ import annotations

from typing import Dict, List

from .bias_plan_candidate import BiasPlanCandidate
from .bias_plan_store import BiasPlanStore


def compute_executive_ranking(plan_store: BiasPlanStore) -> Dict[str, str]:
    """Return a deterministic ranking of strategies per executive goal.

    The ranking follows these deterministic tie‑breakers (in order):
        1. Higher ``final_score``
        2. Higher ``base_score`` (strategy confidence)
        3. Larger number of supporting policies (len(supporting_policy_ids))
        4. Lexicographically smaller candidate ``id`` (ensures deterministic
           ordering when all else is equal)
    The result is a dict mapping ``goal_id`` → ``strategy_id`` for the top
    candidate per goal.
    """
    # Sort all candidates globally using the deterministic key
    sorted_candidates: List[BiasPlanCandidate] = sorted(
        plan_store.candidates,
        key=lambda c: (
            -c.final_score,
            -c.base_score,
            -len(c.supporting_policy_ids),
            c.id,
        ),
    )
    best_per_goal: Dict[str, str] = {}
    for cand in sorted_candidates:
        if cand.goal_id not in best_per_goal:
            best_per_goal[cand.goal_id] = cand.strategy_id
    return best_per_goal
