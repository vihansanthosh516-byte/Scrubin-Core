# -*- coding: utf-8 -*-
"""Deterministic serialization round‑trip tests for WorldState.

The serialization helpers must produce a stable JSON string and rebuilding the
WorldState from that string must yield an object equal to the original.
"""

from scrubin.api.serialization import serialize_worldstate, deserialize_worldstate
from scrubin.world.state import WorldState


def test_worldstate_round_trip_preserves_equality():
    world = WorldState(tick=42, seed=999)
    payload = serialize_worldstate(world)
    restored = deserialize_worldstate(payload)
    assert world == restored


def test_serialization_is_deterministic():
    world1 = WorldState(tick=3, seed=1)
    world2 = WorldState(tick=3, seed=1)
    json1 = serialize_worldstate(world1)
    json2 = serialize_worldstate(world2)
    assert json1 == json2
