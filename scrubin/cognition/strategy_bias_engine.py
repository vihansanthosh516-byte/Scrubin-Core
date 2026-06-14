"""Deterministic strategy bias generation engine.

Generates ``StrategyBias`` objects from aggregated ``PolicyProfile`` entries.
The bias is currently set to the profile's confidence value (deterministic).
"""

from __future__ import annotations

from typing import List

from .policy_profile import PolicyProfile
from .policy_store import PolicyStore
from .strategy_bias import StrategyBias


def generate_strategy_bias(policy_store: PolicyStore) -> List[StrategyBias]:
    """Generate deterministic bias objects for each strategy.

    For each ``PolicyProfile`` in ``policy_store`` we create a ``StrategyBias``
    where ``bias`` mirrors the profile's ``confidence``. The ``confidence`` field of
    the bias is set equal to the profile's confidence as well, representing the
    certainty of the bias.
    """
    biases: List[StrategyBias] = []
    for profile in policy_store.profiles:
        bias_obj = StrategyBias.create(
            strategy_id=profile.strategy_id,
            bias=profile.confidence,
            confidence=profile.confidence,
            supporting_policy_ids=(profile.id,),
        )
        biases.append(bias_obj)
    return biases
