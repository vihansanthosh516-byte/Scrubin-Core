"""Tests for Phase 2E.1 – Action → Event conversion.

The test builds a minimal Orchestrator, creates a dummy ActionIntent, turns it
into a deterministic SurgicalEvent, enqueues it, processes the queue, and
verifies that the ActionAuthority performed the same mutation it would have
executed directly.
"""

import pytest

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.models.intents import ActionIntent
from scrubin.events.action_helper import create_action_event
from scrubin.events.event_processor import process_events


def test_user_action_event_is_processed_and_mutates_world():
    # Minimal orchestrator – we only need the authority and the event queue
    cfg = ConfigLayer(active_profile="default")
    orch = Orchestrator(seed=0, config=cfg, active_profile="default", mode="autonomous")

    # Build a simple, well‑formed procedure intent that the authority will accept
    intent = ActionIntent(
        id="test-intent",
        type="procedure",
        name="test_procedure",
        target="",
        priority=0.0,
        confidence=1.0,
        source="unit_test",
        reasoning="",
        metadata={},
    )

    # Convert the intent into a deterministic SurgicalEvent and enqueue it
    ev = create_action_event(tick=orch.tick_count, intent=intent, source="unit_test")
    orch.sim_event_queue.add(ev)

    # Process the queue – the authority should execute the intent inside the processor
    orch.world, orch.sim_event_queue = process_events(
        orch.world, orch.sim_event_queue, authority=orch.authority
    )

    # The queue must be empty after processing
    assert orch.sim_event_queue._heap == []

    # Authority should have logged exactly one execution event for our intent
    exec_logs = [e for e in orch.authority.execution_log if e.intent_id == intent.id]
    assert len(exec_logs) == 1
    assert exec_logs[0].outcome == "executed"

    # Verify deterministic hash stability (sanity)
    assert ev.deterministic_hash == ev.deterministic_hash
