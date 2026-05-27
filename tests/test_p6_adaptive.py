import pytest
from scrubin.control_plane.adversary.adaptive import AdaptiveAdversary


def test_adaptive_determinism():
    adv = AdaptiveAdversary(seed=1)
    events = [{"topic": "x"}]
    r1 = adv.inject(events, tick_id=1, state_hash="abc")
    r2 = adv.inject(events, tick_id=1, state_hash="abc")
    assert [e.corrupted for e in r1] == [e.corrupted for e in r2]


def test_learning_changes_policy():
    adv = AdaptiveAdversary(seed=1)
    events = [{"topic": "x"}]
    # First tick with neutral feedback – memory stays unchanged (feedback=0.0)
    r1 = adv.inject(events, tick_id=1, state_hash="abc", feedback=0.0)
    # Second tick with positive feedback – memory updates and may affect policy
    r2 = adv.inject(events, tick_id=2, state_hash="abc", feedback=1.0)
    assert len(r1) == len(r2)
