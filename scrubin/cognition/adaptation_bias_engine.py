"""Deterministic adaptation bias generation engine.

Creates ``AdaptationBias`` objects from ``AdaptationProfile`` entries.
All operations are pure cognition.
"""

from __future__ import annotations

from typing import List

from .adaptation_profile import AdaptationProfile
from .adaptation_store import AdaptationStore
from .adaptation_bias import AdaptationBias


def generate_adaptation_biases(adaptation_store: AdaptationStore) -> List[AdaptationBias]:
    """Generate deterministic adaptation bias objects for each profile.

    Bias = average_delta * confidence (deterministic product).
    Confidence is taken from the profile.
    """
    biases: List[AdaptationBias] = []
    for profile in adaptation_store.profiles:
        bias_val = profile.average_delta * profile.confidence
        bias = AdaptationBias.create(
            strategy_id=profile.strategy_id,
            bias=bias_val,
            confidence=profile.confidence,
            supporting_profile_ids=(profile.id,),
        )
        biases.append(bias)
    return biases
