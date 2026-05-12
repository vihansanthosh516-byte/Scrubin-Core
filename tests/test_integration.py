from scrubin.core.orchestrator import Orchestrator
from scrubin.replay.hash import world_hash
from scrubin.replay.canonical import canonical_json
from scrubin.contracts.exceptions import InvariantFatalError


def test_orchestrator_10_ticks():
    o = Orchestrator(snapshot_interval=3)
    o.setup()
    for i in range(10):
        result = o.tick()
        assert result["orchestrator_tick"] == i + 1
    assert o.tick_count == 10


def test_orchestrator_hash_evolution():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    hashes = []
    for _ in range(5):
        o.tick()
        hashes.append(world_hash(o.world))
    assert len(set(hashes)) == 5, "All 5 tick hashes should be unique"


def test_orchestrator_snapshots_at_interval():
    o = Orchestrator(snapshot_interval=2)
    o.setup()
    for _ in range(10):
        o.tick()
    ticks = [s.tick for s in o.snapshot_engine.snapshots]
    assert ticks == [2, 4, 6, 8, 10]


def test_orchestrator_transitions_recorded():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    for _ in range(5):
        o.tick()
    assert o.transition_auditor.count == 5


def test_orchestrator_profiler_profiles():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    for _ in range(5):
        o.tick()
    assert len(o.profiler.profiles) == 5


def test_orchestrator_perf_metrics():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    for _ in range(5):
        o.tick()
    assert len(o.perf_metrics.tick_metrics) == 5


def test_orchestrator_snapshot_restore():
    o = Orchestrator(snapshot_interval=2)
    o.setup()
    for _ in range(6):
        o.tick()
    snaps = o.snapshot_engine.snapshots
    last_snap = snaps[-1]
    restored = o.snapshot_engine.restore(last_snap)
    assert world_hash(restored) == last_snap.world_hash


def test_orchestrator_no_budget_violations():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    for _ in range(10):
        o.tick()
    violations = o.perf_metrics.budget_violations
    assert len(violations) == 0, f"Unexpected budget violations: {violations}"


def test_orchestrator_invariant_validator_present():
    o = Orchestrator()
    assert o.invariant_validator is not None
    assert len(o.invariant_validator.invariants) >= 11


def test_orchestrator_reset():
    o = Orchestrator(snapshot_interval=2)
    o.setup()
    for _ in range(5):
        o.tick()
    o.reset()
    assert o.tick_count == 0
    assert o.transition_auditor.count == 0
    assert len(o.snapshot_engine.snapshots) == 0
    assert len(o.profiler.profiles) == 0


def test_orchestrator_ledger_has_hash_events():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    o.tick()
    events = [e for e in o.ledger.all() if e.type == "world_hash_generated"]
    assert len(events) == 1


def test_orchestrator_ledger_has_transition_audit():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    o.tick()
    events = [e for e in o.ledger.all() if e.type == "state_transition_audit"]
    assert len(events) == 1


def test_orchestrator_to_dict_from_dict_roundtrip():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    o.tick()
    d = o.world.to_dict()
    w2 = type(o.world).from_dict(d)
    h1 = world_hash(o.world)
    h2 = world_hash(w2)
    assert h1 == h2, f"Round-trip hash mismatch: {h1} != {h2}"


def test_orchestrator_invariant_violation_halts():
    o = Orchestrator(snapshot_interval=50)
    o.setup()
    o.tick()
    o.world.organ_state.cardiovascular.health = -1.0
    try:
        o._evolve_world()
        assert False, "Expected InvariantFatalError"
    except InvariantFatalError:
        pass


TESTS = [
    ("integration: orchestrator 10 ticks", test_orchestrator_10_ticks),
    ("integration: hash evolution unique", test_orchestrator_hash_evolution),
    ("integration: snapshots at interval", test_orchestrator_snapshots_at_interval),
    ("integration: transitions recorded", test_orchestrator_transitions_recorded),
    ("integration: profiler profiles", test_orchestrator_profiler_profiles),
    ("integration: perf metrics", test_orchestrator_perf_metrics),
    ("integration: snapshot restore", test_orchestrator_snapshot_restore),
    ("integration: no budget violations", test_orchestrator_no_budget_violations),
    ("integration: invariant validator present", test_orchestrator_invariant_validator_present),
    ("integration: reset clears state", test_orchestrator_reset),
    ("integration: ledger has hash events", test_orchestrator_ledger_has_hash_events),
    ("integration: ledger has transition audit", test_orchestrator_ledger_has_transition_audit),
    ("integration: to_dict/from_dict round-trip", test_orchestrator_to_dict_from_dict_roundtrip),
    ("integration: invariant violation halts", test_orchestrator_invariant_violation_halts),
]
