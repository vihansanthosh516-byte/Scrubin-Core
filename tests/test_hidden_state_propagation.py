'''Tests for the deterministic hidden-state propagation engine.

These tests verify that the per-tick rules defined in ``scrubin.engine.hidden_state_propagation`` correctly mutate the mutable ``SimulationWorld`` instance and that the integration inside ``Orchestrator`` behaves as expected.
'''

import pytest

from scrubin.world.model import SimulationWorld
from scrubin.engine.hidden_state_propagation import apply_hidden_state_propagation
from scrubin.clinical.cognition.diagnostics import HiddenCondition
from scrubin.events.event_queue import EventQueue
from scrubin.events.event_processor import process_events


def _apply_hidden_state(world):
    events = apply_hidden_state_propagation(world)
    q = EventQueue()
    for ev in events:
        q.add(ev)
    world, _ = process_events(world, q)
    return world


def test_vessel_torn_progression():
    """A torn vessel should bleed and reduce visibility each tick."""
    w = SimulationWorld()
    w.hidden_state["vessel_torn"] = True
    w.hidden_state["blood_loss"] = 0
    w.hidden_state["visibility"] = 100

    # First tick
    w = _apply_hidden_state(w)
    assert w.hidden_state["blood_loss"] == 10
    assert w.hidden_state["visibility"] == 95

    # Second tick
    w = _apply_hidden_state(w)
    assert w.hidden_state["blood_loss"] == 20
    assert w.hidden_state["visibility"] == 90


def test_thermal_damage_creates_sepsis():
    """Thermal damage should increase inflammation and eventually create a sepsis hidden condition."""
    w = SimulationWorld()
    w.hidden_state["thermal_damage"] = True
    w.hidden_state["inflammation"] = 0.5

    # Run a few ticks – still below threshold
    for _ in range(4):
        w = _apply_hidden_state(w)
    assert "sepsis" not in w.hidden_state
    # Continue until inflammation exceeds 0.6
    for _ in range(3):
        w = _apply_hidden_state(w)
    assert "sepsis" in w.hidden_state
    sepsis = w.hidden_state["sepsis"]
    assert isinstance(sepsis, HiddenCondition)
    assert sepsis.severity == "high"


def test_orchestrator_integration_hidden_progression():
    """Ensure the orchestrator invokes the hidden-state engine after world evolution."""
    from scrubin.core.orchestrator import Orchestrator
    from scrubin.core.config import ConfigLayer
    from scrubin.patient.profile import STANDARD_PATIENT

    cfg = ConfigLayer(active_profile="default")
    orch = Orchestrator(seed=1, config=cfg, active_profile="default", patient_profile=STANDARD_PATIENT, mode="autonomous")
    # Seed a hidden flag
    orch.world.hidden_state["vessel_torn"] = True
    orch.world.hidden_state["blood_loss"] = 0
    orch.world.hidden_state["visibility"] = 100

    # First simulation tick – should apply hidden progression after evolve()
    orch.tick()
    assert orch.world.hidden_state["blood_loss"] == 10
    assert orch.world.hidden_state["visibility"] == 95
