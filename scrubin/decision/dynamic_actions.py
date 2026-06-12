"""Dynamic action generation based on world hidden_state and current phase.

This module defines a simple rule‑engine that inspects the simulation world’s
hidden_state (an arbitrary dict populated by complications, bleeding events,
instrument actions, etc.) and produces a list of ``DecisionOption`` objects that
represent context‑specific actions. The rules are intentionally lightweight and
data‑driven so they can be extended without modifying code.
"""

from __future__ import annotations

from typing import List

from scrubin.models.types import DecisionOption, VitalDelta

# ---------------------------------------------------------------------------
# Helper: map a plain dict description to a DecisionOption instance.
# ---------------------------------------------------------------------------

def _option_from_dict(d: dict) -> DecisionOption:
    """Create a ``DecisionOption`` from a minimal descriptor dict.

    Expected keys:
        - id (str): unique identifier for the option.
        - label (str): UI label.
        - archetype (str, optional): category (defaults to ``"dynamic"``).
        - impact (dict, optional): vital delta mapping.
        - risk_level (str, optional): ``"low"``, ``"medium"`` or ``"high"``.
    """
    return DecisionOption(
        id=d["id"],
        label=d["label"],
        archetype=d.get("archetype", "dynamic"),
        expected_impact=VitalDelta(**d.get("impact", {})),
        risk_level=d.get("risk_level", "low"),
        target_complication="",
    )

# ---------------------------------------------------------------------------
# Rule definitions – can be moved to a JSON/YAML file later.
# ---------------------------------------------------------------------------

# Example vessel‑tear actions (used when hidden_state["vessel_torn"] == True)
_VESSEL_TEAR_ACTIONS = [
    {"id": "clip_vessel", "label": "Clip Vessel", "risk_level": "low"},
    {"id": "bipolar_cautery", "label": "Bipolar Cautery", "risk_level": "low"},
    {"id": "suction", "label": "Suction", "risk_level": "low"},
    {"id": "pack", "label": "Pack", "risk_level": "medium"},
    {"id": "continue_dissection", "label": "Continue Dissection", "risk_level": "low"},
    {"id": "convert_to_open", "label": "Convert to Open", "risk_level": "high"},
]

# Low visibility actions (when hidden_state["visibility"] < 50)
_VISIBILITY_ACTIONS = [
    {"id": "increase_lighting", "label": "Increase Lighting", "risk_level": "low"},
    {"id": "suction", "label": "Suction", "risk_level": "low"},
    {"id": "irrigate", "label": "Irrigate", "risk_level": "low"},
]

# High blood‑loss actions (when hidden_state["blood_loss"] > 100)
_BLOOD_LOSS_ACTIONS = [
    {"id": "iv_fluids", "label": "IV Fluids", "risk_level": "low"},
    {"id": "blood_transfusion", "label": "Blood Transfusion", "risk_level": "medium"},
    {"id": "apply_hemostat", "label": "Apply Hemostat", "risk_level": "low"},
]

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_dynamic_options(world, phase_id: str | None = None) -> List[DecisionOption]:
    """Generate a list of ``DecisionOption`` objects based on the world state.

    Parameters
    ----------
    world: ``scrubin.world.model.SimulationWorld``
        The mutable simulation world. Only ``hidden_state`` is consulted; the
        function does **not** mutate the world.
    phase_id: str | None
        Identifier of the current surgical phase (e.g., ``"mobilize_appendix"``).
        The function currently uses it only for future extensibility.
    """
    opts: List[DecisionOption] = []
    hs = getattr(world, "hidden_state", {}) or {}

    # --- Vessel tear rule --------------------------------------------------
    if hs.get("vessel_torn"):
        for desc in _VESSEL_TEAR_ACTIONS:
            opts.append(_option_from_dict(desc))

    # --- Visibility rule ---------------------------------------------------
    visibility = hs.get("visibility")
    if isinstance(visibility, (int, float)) and visibility < 50:
        for desc in _VISIBILITY_ACTIONS:
            opts.append(_option_from_dict(desc))

    # --- Blood loss rule ---------------------------------------------------
    blood_loss = hs.get("blood_loss")
    if isinstance(blood_loss, (int, float)) and blood_loss > 100:
        for desc in _BLOOD_LOSS_ACTIONS:
            opts.append(_option_from_dict(desc))

    # --- Phase‑specific placeholder (future extensibility) ---------------
    if phase_id:
        # Example: different phases could enable instrument‑specific actions.
        # For now we leave this hook empty.
        pass

    return opts
