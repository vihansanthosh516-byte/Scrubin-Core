"""Immutable deterministic strategy bias model.

A ``StrategyBias`` represents a deterministic bias value for a strategy derived
from its associated policy profiles. The model is immutable; updates are performed
via ``replace``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_strategy_bias_id(strategy_id: str, supporting_policy_ids: Tuple[str, ...]) -> str:
    """Deterministic identifier for a ``StrategyBias``.

    The ID is ``bias-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the ``strategy_id`` and sorted supporting
    policy IDs.
    """
    canonical = json.dumps(
        {
            "strategy_id": strategy_id,
            "supporting_policy_ids": sorted(supporting_policy_ids),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"bias-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_strategy_bias_hash(bias: "StrategyBias") -> str:
    """Deterministic replay hash for a fully populated ``StrategyBias``.
    """
    data = {
        "id": bias.id,
        "strategy_id": bias.strategy_id,
        "bias": bias.bias,
        "confidence": bias.confidence,
        "supporting_policy_ids": list(bias.supporting_policy_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class StrategyBias:
    id: str
    strategy_id: str
    bias: float
    confidence: float
    supporting_policy_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        strategy_id: str,
        bias: float,
        confidence: float,
        supporting_policy_ids: Tuple[str, ...] = (),
    ) -> "StrategyBias":
        bias_id = deterministic_strategy_bias_id(strategy_id, supporting_policy_ids)
        placeholder = StrategyBias(
            id=bias_id,
            strategy_id=strategy_id,
            bias=bias,
            confidence=confidence,
            supporting_policy_ids=supporting_policy_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_strategy_bias_hash(placeholder))
