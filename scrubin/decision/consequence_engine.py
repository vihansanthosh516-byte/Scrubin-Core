"""Deterministic Consequence Engine.

This module provides a pure function ``apply_consequence`` that, given a
``SimulationWorld`` snapshot, a selected ``DecisionOption`` and the current
procedure phase identifier, returns a **new** ``SimulationWorld`` reflecting the
deterministic effect of that action.

All updates are performed without randomness, timestamps, or side‑effects so
that the engine is fully replay‑safe – applying the same action to the same
world state always yields an identical result.

The engine is intentionally lightweight and rule‑driven.  Adding new actions or
modifying existing effects can be done by extending the ``_ACTION_EFFECTS``
dictionary; no code changes are required beyond that.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Callable, Dict, List, Optional

from scrubin.world.model import SimulationWorld
from scrubin.models.types import DecisionOption, VitalDelta

# ---------------------------------------------------------------------------
# Helper: condition utilities (all receive a SimulationWorld and return bool)
# ---------------------------------------------------------------------------

def _always(_: SimulationWorld) -> bool:
    return True

# ---------------------------------------------------------------------------
# Rule table – maps action IDs to a list of effect descriptors.
# Each descriptor can specify:
#   * ``target`` – name of a hidden_state key or a special keyword ("blood_loss",
#                 "visibility", "inflammation", etc.).
#   * ``coeff``  – numeric delta to add (positive or negative).
#   * ``cond``   – a callable ``world -> bool`` that gates the effect.
#   * ``update`` – dict of hidden_state keys to set to concrete values.
# ---------------------------------------------------------------------------

_ACTION_EFFECTS: Dict[str, List[Dict]] = {
    # Example: clipping a torn vessel removes the flag and reduces blood loss.
    "clip_vessel": [
        {"target": "vessel_torn", "update": {"vessel_torn": False}, "cond": _always},
        {"target": "blood_loss", "coeff": -20, "cond": _always},
    ],
    # Monopolar cautery – increases blood loss if visibility is poor and adds
    # inflammation if the tissue is friable (simulated via a hidden flag).
    "monopolar_cautery": [
        {
            "target": "blood_loss",
            "coeff": 30,
            "cond": lambda w: w.hidden_state.get("visibility", 100) < 50,
        },
        {
            "target": "inflammation",
            "coeff": 0.1,
            "cond": lambda w: w.hidden_state.get("friable_tissue", False),
        },
        # If the patient is obese, visibility worsens.
        {
            "target": "visibility",
            "coeff": -5,
            "cond": lambda w: "obesity" in w.patient_profile.risk_factors,
        },
    ],
    "suction": [
        {"target": "visibility", "coeff": 10, "cond": _always},
        {"target": "blood_loss", "coeff": -10, "cond": _always},
    ],
    "increase_lighting": [
        {"target": "visibility", "coeff": 5, "cond": _always},
    ],
    "apply_hemostat": [
        {"target": "blood_loss", "coeff": -15, "cond": _always},
    ],
    # Default – no effect (keeps determinism for unknown actions).
}

# ---------------------------------------------------------------------------
# Internal helper to apply a single effect descriptor to a world copy.
# ---------------------------------------------------------------------------

def _apply_effect(world: SimulationWorld, eff: Dict) -> None:
    # Conditional guard
    cond: Callable[[SimulationWorld], bool] = eff.get("cond", _always)
    if not cond(world):
        return

    # Direct hidden_state updates (replace values)
    if "update" in eff:
        for k, v in eff["update"].items():
            world.hidden_state[k] = v
        return

    # Numeric adjustments – target may be a hidden_state key or a top‑level
    # attribute of the world (e.g., ``blood_loss`` is stored in hidden_state).
    target = eff.get("target")
    if target is None:
        return
    coeff = eff.get("coeff", 0)
    # Prefer hidden_state first; fall back to attribute if present.
    if target in world.hidden_state:
        current = world.hidden_state.get(target, 0)
        new_val = current + coeff
        # Clamp to non‑negative for quantities that cannot be negative.
        if isinstance(new_val, (int, float)):
            new_val = max(0, new_val)
        world.hidden_state[target] = new_val
    elif hasattr(world, target):
        current = getattr(world, target, 0)
        new_val = current + coeff
        if isinstance(new_val, (int, float)):
            new_val = max(0, new_val)
        setattr(world, target, new_val)
    else:
        # Unknown target – silently ignore (deterministic no‑op).
        return

# ---------------------------------------------------------------------------
# Recalculate derived metrics (mortality, SOFA, NEWS2) after mutable changes.
# ---------------------------------------------------------------------------

def _recalculate_derived_metrics(world: SimulationWorld) -> None:
    # Import inside function to avoid circular import at module load time.
    from scrubin.clinical.mortality import MortalityModel
    from scrubin.clinical.scoring.sofa import SOFAScore
    from scrubin.clinical.scoring.news2 import NEWS2Score

    # Mortality based on current vitals and hidden state.
    world.mortality_risk = MortalityModel.evaluate(world)
    # SOFA and NEWS2 use the current vitals.
    world.sofa_score = SOFAScore.calculate(world.physiology.vitals, {"renal": world.organ_state.renal})
    world.news2_score = NEWS2Score.calculate(world.physiology.vitals)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_consequence(
    world: SimulationWorld,
    action: DecisionOption,
    phase_id: Optional[str] = None,
) -> SimulationWorld:
    """Return a new ``SimulationWorld`` that reflects the deterministic
    consequences of ``action``.

    Parameters
    ----------
    world: SimulationWorld
        The current immutable world snapshot. It will **not** be mutated.
    action: DecisionOption
        The user‑selected action (as generated by the dynamic action generator).
    phase_id: str | None
        Identifier of the current surgical phase – currently unused but kept for
        future extensibility (phase‑specific rules could be added).

    Returns
    -------
    SimulationWorld
        A deep‑copied world instance with updated hidden_state, vitals, and any
        derived metrics.
    """
    # 1. Deep‑copy to guarantee immutability of the input.
    new_world = deepcopy(world)

    # 2. Look up the rule list for the action ID. Unknown actions produce no
    #    changes, preserving determinism.
    effects = _ACTION_EFFECTS.get(action.id, [])
    for eff in effects:
        _apply_effect(new_world, eff)

    # 3. Re‑compute any derived fields that depend on vitals/hidden_state.
    _recalculate_derived_metrics(new_world)

    return new_world
