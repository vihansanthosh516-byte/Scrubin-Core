import pytest
from scrubin.control_plane.adversary.ecosystem import AdversaryEcosystem
from scrubin.control_plane.adversary.adaptive import AdaptiveAdversary


def test_ecosystem_determinism():
    eco = AdversaryEcosystem(seed=1)
    eco.register("a1", AdaptiveAdversary(seed=1))
    eco.register("a2", AdaptiveAdversary(seed=2))

    events = [{"topic": "x"}]
    r1 = eco.inject_all(events, tick_id=1, state_hash="abc")
    r2 = eco.inject_all(events, tick_id=1, state_hash="abc")

    assert [e.corrupted for e in r1] == [e.corrupted for e in r2]


def test_multiple_adversaries_expand_output():
    eco = AdversaryEcosystem(seed=1)
    eco.register("a1", AdaptiveAdversary(seed=1))
    eco.register("a2", AdaptiveAdversary(seed=2))

    events = [{"topic": "x"}]
    r = eco.inject_all(events, tick_id=1, state_hash="abc")
    # With two adversaries each returning one output, the merged list should be at
    # least as long as the original event list.
    assert len(r) >= len(events)
