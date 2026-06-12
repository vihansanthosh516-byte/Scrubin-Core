"""Tests for Phase 2E.2 – Consequence → Event conversion.

The tests verify that the deterministic consequence engine produces events,
that no direct world mutation occurs, and that processing the events updates the
world state correctly.
"""

import copy
import pytest
from scrubin.world.model import SimulationWorld
from scrubin.models.types import DecisionOption, VitalDelta
from scrubin.decision.consequence_engine import generate_consequence_events, _recalculate_derived_metrics
from scrubin.events.event_processor import process_events
from scrubin.events.event_queue import EventQueue

def _make_option(action_id: str) -> DecisionOption:
    """Utility to create a minimal DecisionOption for a given action ID."""
    return DecisionOption(
        id=action_id,
        label="",
        archetype="procedure",
        expected_impact=VitalDelta(),
        risk_level="low",
    )

def test_consequence_generates_events():
    world = SimulationWorld()
    opt = _make_option("clip_vessel")
    events = generate_consequence_events(world, opt)
    # clip_vessel => update vessel_torn (unknown event type) and blood_loss adjustment
    assert any(e.event_type == "bleeding_event" for e in events)
    # Ensure deterministic IDs – calling twice yields identical IDs
    events2 = generate_consequence_events(world, opt)
    ids1 = [e.event_id for e in events]
    ids2 = [e.event_id for e in events2]
    assert ids1 == ids2

def test_consequence_no_direct_mutation():
    world_before = SimulationWorld()
    world_copy = copy.deepcopy(world_before)
    opt = _make_option("increase_lighting")
    _ = generate_consequence_events(world_before, opt)
    # Original world should remain unchanged
    assert world_before.to_dict() == world_copy.to_dict()

def test_consequence_processor_updates_world():
    world = SimulationWorld()
    opt = _make_option("increase_lighting")
    events = generate_consequence_events(world, opt)
    queue = EventQueue()
    for ev in events:
        queue.add(ev)
    # Process events (no authority needed for pure consequence events)
    new_world, _ = process_events(world, queue, authority=None)
    # Visibility should have increased by 5 (default 100 -> 105)
    assert new_world.hidden_state.get("visibility") == 105
    # Recalculate derived metrics to match original apply_consequence behaviour
    _recalculate_derived_metrics(new_world)
    # Ensure derived metrics are present (mortality, scores)
    assert hasattr(new_world, "mortality_risk")
    assert hasattr(new_world, "sofa_score")
    assert hasattr(new_world, "news2_score")
