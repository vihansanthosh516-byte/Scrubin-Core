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
    """Legacy wrapper that applies consequences directly, retained for backward compatibility.
    Internally calls :func:`generate_consequence_events` and then processes the events.
    """
    # Use the new deterministic pipeline: generate events, process them.
    # Generate deterministic consequence events
    events = generate_consequence_events(world, action, phase_id)
    # Enqueue events into a temporary EventQueue and process them on a copy of the world
    from scrubin.events.event_queue import EventQueue
    temp_queue = EventQueue()
    for ev in events:
        temp_queue.add(ev)
    # Process events without authority (pure world changes)
    from scrubin.events.event_processor import process_events
    new_world, _ = process_events(deepcopy(world), temp_queue, authority=None)
    # Recalculate derived metrics to preserve original behavior
    _recalculate_derived_metrics(new_world)
    return new_world

# New deterministic consequence event generator
def generate_consequence_events(
    world: SimulationWorld,
    action: DecisionOption,
    phase_id: Optional[str] = None,
) -> List[SurgicalEvent]:
    """Generate deterministic ``SurgicalEvent`` objects representing the consequences
    of a ``DecisionOption``.

    The function does **not** mutate ``world``. It evaluates the rule table
    ``_ACTION_EFFECTS`` against the provided ``world`` snapshot and creates a list
    of ``SurgicalEvent`` objects that encode the same state changes.
    """
    from scrubin.events.event import SurgicalEvent
    from scrubin.events import event_types
    from scrubin.clinical.cognition.diagnostics import HiddenCondition
    # EventQueue import not needed for event generation
    # Mapping from hidden_state keys to defined event types (reuse that from hidden_state_propagation)
    _TARGET_EVENT_MAP = {
        "blood_loss": event_types.BLEEDING_EVENT,
        "visibility": event_types.VISIBILITY_EVENT,
        "inflammation": event_types.INFLAMMATION_EVENT,
        "hypotension": event_types.HYPOTENSION_EVENT,
        "sepsis": event_types.SEPSIS_EVENT,
    }

    tick = world.tick
    events: List[SurgicalEvent] = []
    effects = _ACTION_EFFECTS.get(action.id, [])
    for idx, eff in enumerate(effects):
        # Conditional guard
        cond: Callable[[SimulationWorld], bool] = eff.get("cond", _always)
        if not cond(world):
            continue
        # Direct updates – emit one event per key/value pair
        if "update" in eff:
            for k, v in eff["update"].items():
                if isinstance(v, HiddenCondition):
                    payload = {
                        "id": v.id,
                        "severity": v.severity,
                        "observability": v.observability,
                        "progression_rate": v.progression_rate,
                    }
                else:
                    payload = {"value": v}
                event_type = _TARGET_EVENT_MAP.get(k, f"{k}_event")
                event_id = f"{tick}-conseq-{action.id}-{idx}-{k}"
                events.append(
                    SurgicalEvent(
                        event_id=event_id,
                        event_type=event_type,
                        source="consequence_engine",
                        tick=tick,
                        priority=0,
                        payload=payload,
                    )
                )
            continue
        # Numeric adjustments – emit an event describing the delta
        target = eff.get("target")
        coeff = eff.get("coeff", 0)
        if target is not None:
            payload = {"target": target, "coeff": coeff}
            event_type = _TARGET_EVENT_MAP.get(target, f"{target}_event")
            event_id = f"{tick}-conseq-{action.id}-{idx}"
            events.append(
                SurgicalEvent(
                    event_id=event_id,
                    event_type=event_type,
                    source="consequence_engine",
                    tick=tick,
                    priority=0,
                    payload=payload,
                )
            )
    return events

