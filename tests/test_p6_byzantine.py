import pytest
from scrubin.control_plane.adversary.byzantine import ByzantineAdversary, FaultType


def test_byzantine_determinism():
    adv = ByzantineAdversary(seed=42)
    events = [
        {"topic": "monitor", "payload": {"value": 1}},
        {"topic": "intubate", "payload": {"value": 2}},
    ]
    state_hash = "deadbeef"  # dummy hash – any string works
    tick_id = 5
    node_id = "node-1"

    # Run twice with identical context.
    out1 = adv.inject(events, tick_id=tick_id, state_hash=state_hash, node_id=node_id)
    out2 = adv.inject(events, tick_id=tick_id, state_hash=state_hash, node_id=node_id)

    # Length is preserved.
    assert len(out1) == len(events)
    assert len(out2) == len(events)

    # Determinism: the corrupted payloads must be identical.
    assert [e.corrupted for e in out1] == [e.corrupted for e in out2]

    # Fault types must belong to the defined set (including NONE).
    valid = {FaultType.CRASH, FaultType.DELAY, FaultType.EQUIVOCATE, FaultType.FORGE, FaultType.NONE}
    for e in out1:
        assert e.fault_type in valid

    # Changing tick should change the result (sanity check).
    out3 = adv.inject(events, tick_id=tick_id + 1, state_hash=state_hash, node_id=node_id)
    assert [e.corrupted for e in out3] != [e.corrupted for e in out1]
