# -*- coding: utf-8 -*-
"""Deterministic tests for the SessionManager.

These tests verify that identical creation requests and identical actions on
separate sessions produce identical immutable responses, and that the internal
WorldState is only updated via immutable replacements.
"""

import pytest
from scrubin.api.session_manager import SessionManager
from scrubin.api.api_contracts import (
    SimulationCreateRequest,
    SimulationActionRequest,
)


def test_create_session_is_deterministic():
    manager_a = SessionManager()
    manager_b = SessionManager()
    req = SimulationCreateRequest(seed=123, initial_tick=0)
    resp_a = manager_a.create_session(req)
    resp_b = manager_b.create_session(req)
    # Session IDs differ, but the initial worlds must be equal.
    assert resp_a.initial_world_state == resp_b.initial_world_state


def test_apply_identical_action_on_separate_sessions_yields_identical_responses():
    # Two independent managers, each with its own session.
    manager_a = SessionManager()
    manager_b = SessionManager()
    create_req = SimulationCreateRequest(seed=7)
    create_a = manager_a.create_session(create_req)
    create_b = manager_b.create_session(create_req)
    action_a = SimulationActionRequest(
        session_id=create_a.session_id,
        action_type="wait",
        parameters={},
        timestamp=0,
    )
    action_b = SimulationActionRequest(
        session_id=create_b.session_id,
        action_type="wait",
        parameters={},
        timestamp=0,
    )
    resp_a = manager_a.apply_action(action_a)
    resp_b = manager_b.apply_action(action_b)
    # Responses must be identical (world tick, events, etc.).
    assert resp_a == resp_b
    # Ensure the world advanced exactly one tick.
    assert resp_a.world_tick == 1
    assert resp_b.world_tick == 1


def test_get_state_returns_consistent_snapshot():
    manager = SessionManager()
    create_resp = manager.create_session(SimulationCreateRequest(seed=0))
    # Initial state – tick 0, empty timeline.
    state1 = manager.get_state(create_resp.session_id)
    assert state1.world_tick == 0
    assert state1.timeline_events == ()
    # Apply an action to advance the world.
    action_req = SimulationActionRequest(
        session_id=create_resp.session_id,
        action_type="wait",
        parameters={},
        timestamp=0,
    )
    manager.apply_action(action_req)
    state2 = manager.get_state(create_resp.session_id)
    assert state2.world_tick == 1
    assert len(state2.timeline_events) == 1
    assert state2.timeline_events[0].description.startswith("action_performed")
