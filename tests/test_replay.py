import json

from scrubin.world.model import SimulationWorld
from scrubin.clinical.cognition.diagnostics import HiddenCondition, ClinicalFinding
from scrubin.replay.canonical import canonical_json, _stable_serialize
from scrubin.replay.hash import world_hash, ReplayProof
from scrubin.replay.snapshots import SnapshotEngine, WorldSnapshot
from scrubin.replay.storage import SnapshotStorage
from scrubin.replay.recovery import RecoveryEngine
from scrubin.core.ledger import EventLedger


def test_canonical_json_deterministic():
    w = SimulationWorld()
    j1 = canonical_json(w)
    j2 = canonical_json(w)
    assert j1 == j2


def test_canonical_json_sorted_keys():
    w = SimulationWorld()
    j = canonical_json(w)
    parsed = json.loads(j)
    assert _keys_sorted(parsed), "Canonical JSON keys not sorted"


def _keys_sorted(d):
    if isinstance(d, dict):
        keys = list(d.keys())
        if keys != sorted(keys):
            return False
        return all(_keys_sorted(v) for v in d.values())
    if isinstance(d, list):
        return all(_keys_sorted(item) for item in d)
    return True


def test_canonical_json_float_precision():
    result = _stable_serialize(0.123456789)
    assert result == 0.123457, f"Expected rounded float, got {result}"


def test_canonical_json_negative_zero():
    result = _stable_serialize(-0.0)
    assert result == 0.0, f"Expected 0.0 for -0.0, got {result}"


def test_canonical_json_none():
    assert _stable_serialize(None) is None


def test_canonical_json_bool():
    assert _stable_serialize(True) is True
    assert _stable_serialize(False) is False


def test_canonical_json_string():
    assert _stable_serialize("hello") == "hello"


def test_canonical_json_list():
    result = _stable_serialize([3.0, 1.0, 2.0])
    assert result == [3.0, 1.0, 2.0]


def test_world_hash_deterministic():
    w = SimulationWorld()
    h1 = world_hash(w)
    h2 = world_hash(w)
    assert h1 == h2


def test_world_hash_changes_after_evolve():
    w = SimulationWorld()
    h1 = world_hash(w)
    w.evolve()
    h2 = world_hash(w)
    assert h1 != h2, "Hash should change after evolve"


def test_world_hash_length():
    w = SimulationWorld()
    h = world_hash(w)
    assert len(h) == 64, f"SHA-256 hex should be 64 chars, got {len(h)}"


def test_replay_proof_matched():
    w = SimulationWorld()
    h = world_hash(w)
    proof = ReplayProof.verify(w, h)
    assert proof.matched is True


def test_replay_proof_mismatched():
    w = SimulationWorld()
    proof = ReplayProof.verify(w, "0" * 64)
    assert proof.matched is False


def test_snapshot_compress_decompress():
    w = SimulationWorld()
    compressed = SnapshotStorage.compress(w)
    assert isinstance(compressed, bytes)
    restored = SnapshotStorage.decompress(compressed)
    assert isinstance(restored, SimulationWorld)


def test_snapshot_round_trip_hash():
    w = SimulationWorld()
    original_hash = world_hash(w)
    compressed = SnapshotStorage.compress(w)
    restored = SnapshotStorage.decompress(compressed)
    restored_hash = world_hash(restored)
    assert original_hash == restored_hash


def test_snapshot_engine_interval():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=5, ledger=ledger)
    assert engine.interval == 5
    assert engine.should_snapshot(5) is True
    assert engine.should_snapshot(0) is False
    assert engine.should_snapshot(3) is False


def test_snapshot_engine_capture():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    w = SimulationWorld()
    snap = engine.capture(w, tick=1)
    assert snap.tick == 1
    assert snap.world_hash == world_hash(w)
    assert len(snap.compressed_state) > 0
    assert len(engine.snapshots) == 1


def test_snapshot_engine_restore():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    w = SimulationWorld()
    snap = engine.capture(w, tick=1)
    restored = engine.restore(snap)
    assert world_hash(restored) == snap.world_hash


def test_snapshot_engine_latest_before():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    w = SimulationWorld()
    engine.capture(w, tick=5)
    engine.capture(w, tick=10)
    result = engine.latest_before(7)
    assert result is not None
    assert result.tick == 5


def test_snapshot_engine_latest_before_none():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    result = engine.latest_before(3)
    assert result is None


def test_world_snapshot_to_dict():
    snap = WorldSnapshot(tick=1, sequence_id=1, world_hash="abc", compressed_state=b"data")
    d = snap.to_dict()
    assert d["tick"] == 1
    assert d["world_hash"] == "abc"
    assert "compressed_size" in d


def test_recovery_engine_basic():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    recovery = RecoveryEngine(snapshot_engine=engine)
    w = SimulationWorld()
    engine.capture(w, tick=1)
    result = recovery.recover_to_tick(target_tick=1)
    assert result is not None


def test_recovery_engine_no_snapshot():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    recovery = RecoveryEngine(snapshot_engine=engine)
    result = recovery.recover_to_tick(target_tick=5)
    assert result is None


def test_recovery_verify_recovery():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    recovery = RecoveryEngine(snapshot_engine=engine)
    w = SimulationWorld()
    h = world_hash(w)
    result = recovery.verify_recovery(w, h)
    assert result["hash_matched"] is True
    assert result["invariant_violations"] == 0


def test_recovery_verify_mismatch():
    ledger = EventLedger()
    engine = SnapshotEngine(interval=1, ledger=ledger)
    recovery = RecoveryEngine(snapshot_engine=engine)
    w = SimulationWorld()
    result = recovery.verify_recovery(w, "bad_hash")
    assert result["hash_matched"] is False


def test_hidden_condition_to_dict():
    hc = HiddenCondition(id="sepsis", severity="high", onset_tick=5, observability=0.7, progression_rate=0.1)
    d = hc.to_dict()
    assert d["id"] == "sepsis"
    assert d["severity"] == "high"
    assert d["onset_tick"] == 5
    assert d["observability"] == 0.7
    assert d["progression_rate"] == 0.1


def test_hidden_condition_from_dict():
    d = {"id": "sepsis", "severity": "high", "onset_tick": 5, "observability": 0.7, "progression_rate": 0.1}
    hc = HiddenCondition.from_dict(d)
    assert hc.id == "sepsis"
    assert hc.severity == "high"
    assert hc.onset_tick == 5


def test_hidden_condition_round_trip():
    hc = HiddenCondition(id="ards", severity="critical", onset_tick=10, observability=0.5, progression_rate=0.3)
    d = hc.to_dict()
    hc2 = HiddenCondition.from_dict(d)
    assert hc2.id == hc.id
    assert hc2.severity == hc.severity
    assert hc2.onset_tick == hc.onset_tick
    assert hc2.observability == hc.observability
    assert hc2.progression_rate == hc.progression_rate


def test_clinical_finding_to_dict():
    cf = ClinicalFinding(type="hypoxemia", confidence=0.85, source="spo2", supporting_vitals={"spo2": 88})
    d = cf.to_dict()
    assert d["type"] == "hypoxemia"
    assert d["confidence"] == 0.85
    assert d["source"] == "spo2"
    assert d["supporting_vitals"]["spo2"] == 88


def test_clinical_finding_from_dict():
    d = {"type": "hypoxemia", "confidence": 0.85, "source": "spo2", "supporting_vitals": {"spo2": 88}}
    cf = ClinicalFinding.from_dict(d)
    assert cf.type == "hypoxemia"
    assert cf.confidence == 0.85
    assert cf.source == "spo2"


def test_clinical_finding_round_trip():
    cf = ClinicalFinding(type="shock", confidence=0.9, source="bp", supporting_vitals={"map": 55})
    d = cf.to_dict()
    cf2 = ClinicalFinding.from_dict(d)
    assert cf2.type == cf.type
    assert cf2.confidence == cf.confidence
    assert cf2.source == cf.source
    assert cf2.supporting_vitals == cf.supporting_vitals


def test_world_with_hidden_condition_round_trip():
    w = SimulationWorld()
    w.hidden_state["sepsis"] = HiddenCondition(id="sepsis", severity="high", onset_tick=1, observability=0.7, progression_rate=0.1)
    d = w.to_dict()
    w2 = SimulationWorld.from_dict(d)
    assert "sepsis" in w2.hidden_state
    hc = w2.hidden_state["sepsis"]
    assert isinstance(hc, HiddenCondition)
    assert hc.id == "sepsis"


def test_world_with_clinical_finding_round_trip():
    w = SimulationWorld()
    w.observable_state.append(ClinicalFinding(type="fever", confidence=0.95, source="temp"))
    d = w.to_dict()
    w2 = SimulationWorld.from_dict(d)
    assert len(w2.observable_state) == 1
    cf = w2.observable_state[0]
    assert isinstance(cf, ClinicalFinding)
    assert cf.type == "fever"


def test_world_hidden_condition_hash_stable():
    w = SimulationWorld()
    w.hidden_state["ards"] = HiddenCondition(id="ards", severity="critical", onset_tick=3, observability=0.4, progression_rate=0.2)
    h1 = world_hash(w)
    h2 = world_hash(w)
    assert h1 == h2


TESTS = [
    ("replay: canonical JSON deterministic", test_canonical_json_deterministic),
    ("replay: canonical JSON sorted keys", test_canonical_json_sorted_keys),
    ("replay: canonical JSON float precision", test_canonical_json_float_precision),
    ("replay: canonical JSON negative zero", test_canonical_json_negative_zero),
    ("replay: canonical JSON None", test_canonical_json_none),
    ("replay: canonical JSON bool", test_canonical_json_bool),
    ("replay: canonical JSON string", test_canonical_json_string),
    ("replay: canonical JSON list", test_canonical_json_list),
    ("replay: world hash deterministic", test_world_hash_deterministic),
    ("replay: world hash changes after evolve", test_world_hash_changes_after_evolve),
    ("replay: world hash length", test_world_hash_length),
    ("replay: ReplayProof matched", test_replay_proof_matched),
    ("replay: ReplayProof mismatched", test_replay_proof_mismatched),
    ("replay: snapshot compress/decompress", test_snapshot_compress_decompress),
    ("replay: snapshot round-trip hash", test_snapshot_round_trip_hash),
    ("replay: snapshot engine interval", test_snapshot_engine_interval),
    ("replay: snapshot engine capture", test_snapshot_engine_capture),
    ("replay: snapshot engine restore", test_snapshot_engine_restore),
    ("replay: snapshot engine latest_before", test_snapshot_engine_latest_before),
    ("replay: snapshot engine latest_before none", test_snapshot_engine_latest_before_none),
    ("replay: WorldSnapshot to_dict", test_world_snapshot_to_dict),
    ("replay: recovery engine basic", test_recovery_engine_basic),
    ("replay: recovery engine no snapshot", test_recovery_engine_no_snapshot),
    ("replay: recovery verify matched", test_recovery_verify_recovery),
    ("replay: recovery verify mismatched", test_recovery_verify_mismatch),
    ("replay: HiddenCondition to_dict", test_hidden_condition_to_dict),
    ("replay: HiddenCondition from_dict", test_hidden_condition_from_dict),
    ("replay: HiddenCondition round-trip", test_hidden_condition_round_trip),
    ("replay: ClinicalFinding to_dict", test_clinical_finding_to_dict),
    ("replay: ClinicalFinding from_dict", test_clinical_finding_from_dict),
    ("replay: ClinicalFinding round-trip", test_clinical_finding_round_trip),
    ("replay: world with HiddenCondition round-trip", test_world_with_hidden_condition_round_trip),
    ("replay: world with ClinicalFinding round-trip", test_world_with_clinical_finding_round_trip),
    ("replay: world with HiddenCondition hash stable", test_world_hidden_condition_hash_stable),
]
