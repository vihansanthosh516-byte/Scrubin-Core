"""Deterministic predictive engine

Generates future projections (``PredictiveState`` objects) for a set of
``ExecutivePolicyDecision`` instances using deterministic extrapolation based on
policy confidence, arbitration scores, adaptation signals, and counterfactuals.
"""

from __future__ import annotations

import itertools
from typing import List

from .predictive_state import PredictiveState
from .predictive_store import PredictiveStore

# Import required stores for type hints – runtime imports avoid circular deps.
from scrubin.cognition.executive_policy_store import ExecutivePolicyStore
from scrubin.cognition.counterfactual_store import CounterfactualStore
from scrubin.cognition.graph_store import GraphStore
from scrubin.cognition.adaptation_store import AdaptationStore
from scrubin.cognition.policy_store import PolicyStore

# Horizons to predict (ticks ahead)
_PREDICTION_HORIZONS = [1, 5, 10, 25, 50]


def _deterministic_projection(decision_id: str, horizon: int, decision_conf: float, decision_score: float) -> dict:
    """Deterministic placeholder projection calculation.

    Returns a dict with keys ``mortality``, ``sofa``, ``news2``, ``resources``,
    ``complications``, and ``world_hash``. The formulas are simple deterministic
    functions of the inputs; they contain no randomness.
    """
    # Base deterministic values derived from decision metrics.
    base_mort = max(0.0, min(1.0, decision_conf * 0.2 + decision_score * 0.001))
    projected_mortality = min(1.0, base_mort + horizon * 0.0005)
    projected_sofa = min(24.0, decision_score * 5 + horizon * 0.1)
    projected_news2 = min(20.0, decision_conf * 5 + horizon * 0.05)
    # Deterministic resources – derived from decision_id hash fragment.
    seed = int(decision_id[-4:], 16) if len(decision_id) >= 4 else 0
    resources = tuple(sorted({f"resource_{(seed + horizon) % 5}"}))
    # Deterministic complications – simple pattern based on horizon.
    complications = tuple(sorted({f"comp_{horizon}_{i}" for i in range(min(2, horizon // 10 + 1))}))
    # Create a deterministic world hash based on the projected metrics.
    import hashlib, json
    world_data = {
        "mortality": projected_mortality,
        "sofa": projected_sofa,
        "news2": projected_news2,
        "resources": list(resources),
        "complications": list(complications),
    }
    world_hash = hashlib.sha256(json.dumps(world_data, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    return {
        "mortality": projected_mortality,
        "sofa": projected_sofa,
        "news2": projected_news2,
        "resources": resources,
        "complications": complications,
        "world_hash": world_hash,
    }


def update_predictive_states(
    executive_policy_store: ExecutivePolicyStore,
    counterfactual_store: CounterfactualStore,
    graph_store: GraphStore,
    adaptation_store: AdaptationStore,
    policy_store: PolicyStore,
    predictive_store: PredictiveStore,
) -> None:
    """Generate deterministic predictive states for each executive policy decision.

    The function loops over all ``ExecutivePolicyDecision`` objects currently in
    ``executive_policy_store`` and creates ``PredictiveState`` objects for each
    configured horizon. The resulting states are added to ``predictive_store`` via
    its ``add_or_update`` method.
    """
    decisions = executive_policy_store.decisions
    for decision in decisions:
        for horizon in _PREDICTION_HORIZONS:
            proj = _deterministic_projection(
                decision_id=decision.id,
                horizon=horizon,
                decision_conf=decision.confidence,
                decision_score=decision.arbitration_score,
            )
            # Supporting counterfactual IDs – take up to two from the store.
            cf_ids = tuple(sorted([cf.id for cf in itertools.islice(counterfactual_store.scenarios(), 2)]))
            state = PredictiveState.create(
                source_tick=decision.first_seen_tick,
                horizon=horizon,
                projected_world_hash=proj["world_hash"],
                projected_mortality=proj["mortality"],
                projected_sofa=proj["sofa"],
                projected_news2=proj["news2"],
                projected_resources=proj["resources"],
                projected_complications=proj["complications"],
                supporting_counterfactual_ids=cf_ids,
            )
            predictive_store.add_or_update(state)
