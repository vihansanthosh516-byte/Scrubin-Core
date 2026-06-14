"""Immutable deterministic predictive state model.

Represents a deterministic forecast of the world state for a given horizon.
All fields are frozen; instances are created via the ``create`` factory which
computes a deterministic identifier and replay hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Tuple


def deterministic_predictive_state_id(source_tick: int, horizon: int, decision_id: str) -> str:
    """Deterministic identifier for a ``PredictiveState``.

    The identifier is ``predictive-`` plus the first 12 hex characters of a
    SHA‑256 hash over a canonical JSON representation of ``source_tick``,
    ``horizon`` and the ``decision_id`` that generated the prediction.
    """
    canonical = json.dumps(
        {
            "source_tick": source_tick,
            "horizon": horizon,
            "decision_id": decision_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"predictive-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_predictive_state_hash(state: "PredictiveState") -> str:
    """Deterministic replay hash for a fully populated ``PredictiveState``.

    All fields (including the identifier) are included in the hash to ensure
    replay safety.
    """
    data = {
        "id": state.id,
        "source_tick": state.source_tick,
        "horizon": state.horizon,
        "projected_world_hash": state.projected_world_hash,
        "projected_mortality": state.projected_mortality,
        "projected_sofa": state.projected_sofa,
        "projected_news2": state.projected_news2,
        "projected_resources": list(state.projected_resources),
        "projected_complications": list(state.projected_complications),
        "supporting_counterfactual_ids": list(state.supporting_counterfactual_ids),
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class PredictiveState:
    """Immutable deterministic prediction of future world metrics.

    Attributes
    ----------
    id: str
        Deterministic identifier derived from ``source_tick``, ``horizon`` and the
        originating decision identifier.
    source_tick: int
        The tick at which the prediction was generated.
    horizon: int
        Number of ticks into the future the projection covers.
    projected_world_hash: str
        Deterministic hash representing the projected world state.
    projected_mortality: float
        Expected mortality risk (0‑1).
    projected_sofa: float
        Expected SOFA score.
    projected_news2: float
        Expected NEWS2 score.
    projected_resources: Tuple[str, ...]
        Deterministic set of resource identifiers expected to be needed.
    projected_complications: Tuple[str, ...]
        Deterministic set of complication identifiers expected to arise.
    supporting_counterfactual_ids: Tuple[str, ...]
        Counterfactual scenario identifiers that contributed to this projection.
    replay_hash: str
        Deterministic replay hash for the full object.
    """

    id: str
    source_tick: int
    horizon: int
    projected_world_hash: str
    projected_mortality: float
    projected_sofa: float
    projected_news2: float
    projected_resources: Tuple[str, ...]
    projected_complications: Tuple[str, ...]
    supporting_counterfactual_ids: Tuple[str, ...]
    replay_hash: str

    @staticmethod
    def create(
        source_tick: int,
        horizon: int,
        projected_world_hash: str,
        projected_mortality: float,
        projected_sofa: float,
        projected_news2: float,
        projected_resources: Tuple[str, ...],
        projected_complications: Tuple[str, ...],
        supporting_counterfactual_ids: Tuple[str, ...],
    ) -> "PredictiveState":
        """Factory that creates a deterministic ``PredictiveState`` instance.
        """
        # The deterministic identifier is based on the source tick, horizon and a
        # placeholder decision identifier (derived from the projected world hash).
        # In practice the decision identifier is part of the caller's context.
        # Here we use ``projected_world_hash`` as a surrogate to guarantee
        # determinism without requiring the decision object.
        decision_id = projected_world_hash[:12]
        state_id = deterministic_predictive_state_id(source_tick, horizon, decision_id)
        placeholder = PredictiveState(
            id=state_id,
            source_tick=source_tick,
            horizon=horizon,
            projected_world_hash=projected_world_hash,
            projected_mortality=projected_mortality,
            projected_sofa=projected_sofa,
            projected_news2=projected_news2,
            projected_resources=projected_resources,
            projected_complications=projected_complications,
            supporting_counterfactual_ids=supporting_counterfactual_ids,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_predictive_state_hash(placeholder))
