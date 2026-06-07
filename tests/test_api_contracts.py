# -*- coding: utf-8 -*-
"""Tests for API contract immutability and basic properties.

The contracts must be frozen dataclasses – attempts to modify fields should raise
``FrozenInstanceError``.  This ensures the frontend cannot accidentally mutate a
request or response object.
"""

import pytest
from dataclasses import FrozenInstanceError

from scrubin.api.api_contracts import (
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationActionRequest,
    SimulationActionResponse,
    SimulationStateResponse,
)
from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent


def test_simulation_create_request_is_frozen():
    req = SimulationCreateRequest(seed=42)
    with pytest.raises(FrozenInstanceError):
        req.seed = 1  # type: ignore


def test_simulation_action_request_is_frozen():
    req = SimulationActionRequest(session_id="sid", action_type="wait")
    with pytest.raises(FrozenInstanceError):
        req.action_type = "inspect"  # type: ignore


def test_simulation_create_response_is_frozen():
    world = WorldState(tick=0, seed=0)
    resp = SimulationCreateResponse(session_id="abc", initial_world_state=world)
    with pytest.raises(FrozenInstanceError):
        resp.session_id = "def"  # type: ignore


def test_simulation_action_response_is_frozen():
    world = WorldState(tick=1, seed=0)
    ev = TimelineEvent(tick=0, description="action_performed:wait")
    resp = SimulationActionResponse(
        world_tick=world.tick,
        timeline_events=(ev,),
        updated_score=0.0,
        updated_world_state=world,
        active_goals=(),
        active_intents=(),
        reflection_summary=world.reflection_state,
        learning_summary=world.learning_state,
    )
    with pytest.raises(FrozenInstanceError):
        resp.world_tick = 2  # type: ignore


def test_simulation_state_response_is_frozen():
    world = WorldState(tick=0, seed=0)
    resp = SimulationStateResponse(
        world_tick=world.tick,
        timeline_events=world.timeline,
        updated_score=0.0,
        current_world_state=world,
        active_goals=(),
        active_intents=(),
        reflection_summary=world.reflection_state,
        learning_summary=world.learning_state,
    )
    with pytest.raises(FrozenInstanceError):
        resp.updated_score = 1.0  # type: ignore
