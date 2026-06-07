"""Phase P.7 – Distributed deterministic replay tests.

These tests verify that two simulated nodes can claim ownership of a session,
store events, take snapshots, and later reconstruct identical ``WorldState``
instances without any nondeterministic divergence.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from scrubin.world.state import WorldState
from scrubin.api.session_manager import SessionManager
from scrubin.api.persistent_session_store import PersistentSessionStore
from scrubin.api.api_contracts import SimulationActionRequest, SimulationCreateRequest
from scrubin.runtime.event_log import EventLog, SessionEvent
from scrubin.runtime.snapshot_store import SnapshotStore
from scrubin.runtime.node_manager import NodeRegistry


def _apply_event(manager: SessionManager, event: SessionEvent) -> None:
    # Build a SimulationActionRequest compatible with the manager.
    action_req = SimulationActionRequest(
        session_id=event.session_id,
        action_type=event.action_type,
        parameters=event.parameters,
        timestamp=event.tick,
    )
    manager.apply_action(action_req)


def test_cross_node_replay_consistency():
    # ----- Setup shared infrastructure -----
    event_log = EventLog()
    tmp_snap_dir = tempfile.mkdtemp()
    snapshot_store = SnapshotStore(base_dir=tmp_snap_dir)
    node_registry = NodeRegistry()
    node_registry.register_node("node_a")
    node_registry.register_node("node_b")

    # ----- Node A creates session and processes actions -----
    node_a_id = "node_a"
    session_id = "sess123"
    assert node_registry.claim(session_id, node_a_id)

    manager_a = SessionManager()
    # Create a session with a deterministic seed
    create_req = SimulationCreateRequest(seed=42, initial_tick=0)
    resp = manager_a.create_session(create_req, user_id="default_user")
    # Ensure the created session matches our expected ID
    # (SessionManager generates a random ID, so we replace it for test purposes)
    # For deterministic testing we manually set the session id mapping.
    manager_a._sessions[session_id] = manager_a._sessions.pop(resp.session_id)
    manager_a._owners[session_id] = "default_user"

    # Save initial snapshot (empty world before any actions)
    snapshot_store.save_snapshot(session_id, manager_a._sessions[session_id])

    # Simulate a series of actions
    actions = [
        SessionEvent(session_id=session_id, tick=1, action_type="test_action", parameters={}, seed=42),
        SessionEvent(session_id=session_id, tick=2, action_type="test_action", parameters={}, seed=42),
        SessionEvent(session_id=session_id, tick=3, action_type="test_action", parameters={}, seed=42),
    ]
    for ev in actions:
        event_log.append(ev)
        _apply_event(manager_a, ev)

    # Release ownership from Node A (no additional snapshot needed)
    assert node_registry.release(session_id, node_a_id)

    # ----- Node B reclaims session and rebuilds state -----
    node_b_id = "node_b"
    assert node_registry.claim(session_id, node_b_id)
    manager_b = SessionManager()
    # Load latest snapshot
    snapshot = snapshot_store.load_snapshot(session_id)
    assert snapshot is not None
    manager_b._sessions[session_id] = snapshot
    manager_b._owners[session_id] = "default_user"
    # Replay events that occurred after the snapshot (none in this simple case)
    for ev in event_log.get_events(session_id):
        _apply_event(manager_b, ev)

    # Final worlds must be identical
    world_a = manager_a._sessions[session_id]
    world_b = manager_b._sessions[session_id]
    assert world_a == world_b
