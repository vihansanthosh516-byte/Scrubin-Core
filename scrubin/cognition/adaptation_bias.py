"""Immutable deterministic adaptation bias model.

Derived from ``AdaptationProfile`` – captures a bias value for a strategy based on
past adaptation performance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_adaptation_bias_id(strategy_id: str) -> str:
    """Deterministic identifier for an ``AdaptationBias``.

    The ID is ``adaptbias-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the ``strategy_id``.
    """
    canonical = json.dumps({"strategy_id": strategy_id}, separators=(",", ":"), sort_keys=True)
    return f"adaptbias-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_adaptation_bias_hash(bias: "AdaptationBias") -> str:
    """Deterministic replay hash for a fully populated ``AdaptationBias``.
    """
    data = {
        "id": bias.id,
        "strategy_id": bias.strategy_id,
        "bias": bias.bias,
        "confidence": bias.confidence,
        "supporting_profile_ids": list(bias.supporting_profile_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class AdaptationBias:
    """Immutable bias derived from adaptation profile.

    ``bias`` – ``average_delta * confidence`` (deterministic).
    """
    id: str
    strategy_id: str
    bias: float
    confidence: float
    supporting_profile_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        bias: float,
        confidence: float,
        supporting_profile_ids: Tuple[str, ...] = (),
    ) -> "AdaptationBias":
        bias_id = deterministic_adaptation_bias_id(strategy_id)
        placeholder = AdaptationBias(
            id=bias_id,
            strategy_id=strategy_id,
            bias=bias,
            confidence=confidence,
            supporting_profile_ids=supporting_profile_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_adaptation_bias_hash(placeholder))
