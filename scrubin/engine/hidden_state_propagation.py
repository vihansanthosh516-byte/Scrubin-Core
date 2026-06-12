"""Hidden State Propagation Engine.

This module provides a deterministic, per‑tick progression of hidden
state variables.  Rules are defined in ``_PROGRESSION_RULES`` – each key
corresponds to a hidden‑state flag; when the flag is present (and truthy)
the associated effects are applied each tick.  Effects can update numeric
values, set flags, or create ``HiddenCondition`` objects.

The engine mutates the provided ``SimulationWorld`` in‑place, matching the
behaviour of ``SimulationWorld.evolve``.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Any

from scrubin.world.model import SimulationWorld
from scrubin.clinical.cognition.diagnostics import HiddenCondition

# ---------------------------------------------------------------------------
# Helper: unconditional guard
# ---------------------------------------------------------------------------

def _always(_: SimulationWorld) -> bool:
    """Always true condition – used as default guard."""
    return True

# ---------------------------------------------------------------------------
# Rule table – maps hidden‑state keys to a list of effect descriptors.
# Each descriptor may contain:
#   * ``target`` – name of a hidden_state key (or top‑level attribute) to adjust.
#   * ``coeff``  – numeric delta to add (positive or negative).
#   * ``cond``   – callable ``world -> bool`` that gates the effect.
#   * ``update`` – dict of hidden_state keys to set to concrete values (e.g.,
#                  creating a ``HiddenCondition`` when a threshold is met).
# ---------------------------------------------------------------------------

_PROGRESSION_RULES: Dict[str, List[Dict]] = {
    # Example: a torn vessel bleeds and reduces visibility each tick.
    "vessel_torn": [
        {"target": "blood_loss", "coeff": 10, "cond": _always},
        {"target": "visibility",  "coeff": -5, "cond": _always},
    ],
    # Thermal injury generates inflammation; when inflammation passes a
    # threshold we create a sepsis hidden condition.
    "thermal_damage": [
        {"target": "inflammation", "coeff": 0.02, "cond": _always},
        {
            "target": "sepsis",
            "update": {
                "sepsis": HiddenCondition(
                    id="sepsis",
                    severity="high",
                    onset_tick=None,  # will be filled in below
                    observability=0.7,
                    progression_rate=0.1,
                )
            },
            "cond": lambda w: w.hidden_state.get("inflammation", 0) > 0.6,
        },
    ],
    # Accumulated blood loss may trigger a hypotension flag.
    "blood_loss": [
        {
            "target": "hypotension",
            "update": {"hypotension": True},
            "cond": lambda w: w.hidden_state.get("blood_loss", 0) > 200,
        },
    ],
}

# ---------------------------------------------------------------------------
# Internal helper to apply a single effect descriptor to the world.
# ---------------------------------------------------------------------------

def _apply_effect(world: SimulationWorld, eff: Dict) -> None:
    # Conditional guard
    cond: Callable[[SimulationWorld], bool] = eff.get("cond", _always)
    if not cond(world):
        return

    # Direct hidden_state updates (replace values)
    if "update" in eff:
        for k, v in eff["update"].items():
            # If we are inserting a HiddenCondition, set its onset_tick to current tick.
            if isinstance(v, HiddenCondition):
                v = HiddenCondition(
                    id=v.id,
                    severity=v.severity,
                    onset_tick=world.tick,
                    observability=v.observability,
                    progression_rate=v.progression_rate,
                )
            world.hidden_state[k] = v
        return

    # Numeric adjustments – target may be a hidden_state key or a top‑level attribute.
    target = eff.get("target")
    if target is None:
        return
    coeff = eff.get("coeff", 0)
    # Prefer hidden_state first; fall back to attribute if present.
    if target in world.hidden_state:
        current = world.hidden_state.get(target, 0)
        new_val = current + coeff
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
# Public API – apply progression for the current tick.
# ---------------------------------------------------------------------------

def apply_hidden_state_propagation(world: SimulationWorld) -> List[SurgicalEvent]:
    """Progress hidden‑state effects for the current tick and emit events.

    Instead of mutating the world directly, this function generates a list of
    deterministic ``SurgicalEvent`` objects that describe the changes.  The
    caller (e.g., ``Orchestrator``) should enqueue these events and let the
    ``event_processor`` apply them to the immutable world state.
    """
    from uuid import uuid4
    from scrubin.events.event import SurgicalEvent
    from scrubin.events import event_types
    # Mapping from hidden_state keys to defined event types
    _TARGET_EVENT_MAP = {
        "blood_loss": event_types.BLEEDING_EVENT,
        "visibility": event_types.VISIBILITY_EVENT,
        "inflammation": event_types.INFLAMMATION_EVENT,
        "hypotension": event_types.HYPOTENSION_EVENT,
        "sepsis": event_types.SEPSIS_EVENT,
    }

    events: List[SurgicalEvent] = []
    tick = world.tick
    # Helper to create an event
    def _make_event(event_type: str, payload: Dict[str, Any]) -> SurgicalEvent:
        return SurgicalEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            source="hidden_state_propagation",
            tick=tick,
            priority=0,
            payload=payload,
        )

    for key, rule_set in _PROGRESSION_RULES.items():
        if world.hidden_state.get(key):
            for eff in rule_set:
                # Conditional guard
                cond: Callable[[SimulationWorld], bool] = eff.get("cond", _always)
                if not cond(world):
                    continue
                # Direct updates – emit a specific event for each key/value
                if "update" in eff:
                    for k, v in eff["update"].items():
                        if isinstance(v, HiddenCondition):
                            payload = {
                                "id": v.id,
                                "severity": v.severity,
                                "observability": v.observability,
                                "progression_rate": v.progression_rate,
                            }
                            event_type = _TARGET_EVENT_MAP.get(k, f"{k}_event")
                            events.append(_make_event(event_type, payload))
                        else:
                            payload = {"value": v}
                            event_type = _TARGET_EVENT_MAP.get(k, f"{k}_event")
                            events.append(_make_event(event_type, payload))
                    continue
                # Numeric adjustments – emit an event describing the delta
                target = eff.get("target")
                coeff = eff.get("coeff", 0)
                if target is not None:
                    payload = {"target": target, "coeff": coeff}
                    event_type = _TARGET_EVENT_MAP.get(target, f"{target}_event")
                    events.append(_make_event(event_type, payload))
    return events
