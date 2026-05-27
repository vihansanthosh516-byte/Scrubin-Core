import pytest
from scrubin.control_plane.p6_kernel import P6Kernel


def test_kernel_initialisation():
    kernel = P6Kernel(core_interface=None)
    assert isinstance(kernel, P6Kernel)
    # Core components should be present
    assert hasattr(kernel, "replay_executor")
    assert hasattr(kernel, "snapshot_manager")
    assert hasattr(kernel, "_chaos_generator")


def test_adversary_injection_returns_mutated_events():
    kernel = P6Kernel(core_interface=None)
    events = [{"action": "monitor", "params": {}}, {"action": "intubate", "params": {}}]
    mutated = kernel.inject_adversary(events, seed=42)
    # The returned list should be a list and not be the exact same object
    assert isinstance(mutated, list)
    assert mutated is not events
    # Length may change due to duplicate mutator; ensure it's still a list of dicts
    assert all(isinstance(e, dict) for e in mutated)


def test_snapshot_and_rollback_roundtrip():
    kernel = P6Kernel(core_interface=None)
    session_id = "test_sess"
    tick = 5
    state = {"tick": tick, "value": 123}
    snap_id = kernel.capture_snapshot(session_id, tick, state)
    assert isinstance(snap_id, str) and snap_id.startswith("snap-")
    restored = kernel.rollback_to_snapshot(snap_id)
    assert restored == state


def test_hash_state_returns_hex_string():
    kernel = P6Kernel(core_interface=None)
    world = {"physiology": {"vitals": {"bp_systolic": 120}}, "organ_state": {}}
    h = kernel.hash_state(world)
    # SHA‑256 hex strings are 64 characters long and consist of hex digits
    assert isinstance(h, str)
    assert len(h) == 64
    int(h, 16)  # should not raise ValueError


def test_reconstruct_session_returns_dict_structure():
    kernel = P6Kernel(core_interface=None)
    result = kernel.reconstruct_session("nonexistent")
    # ReplayExecutor returns a dict even if the session does not exist
    assert isinstance(result, dict)
    assert set(result.keys()) == {"final_state", "snapshots", "execution_order"}
