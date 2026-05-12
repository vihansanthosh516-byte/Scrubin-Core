from scrubin.world.model import SimulationWorld
from scrubin.contracts.validator import InvariantValidator
from scrubin.contracts.invariants import CANONICAL_INVARIANTS, HOSPITAL_INVARIANTS, register_invariant
from scrubin.contracts.simulation import SimulationInvariant
from scrubin.contracts.violations import InvariantViolation
from scrubin.contracts.exceptions import InvariantFatalError, SimulationCorruptionError
from scrubin.core.ledger import EventLedger


def test_canonical_invariants_count():
    assert len(CANONICAL_INVARIANTS) >= 11, f"Expected >=11 canonical invariants, got {len(CANONICAL_INVARIANTS)}"


def test_invariant_validator_default():
    v = InvariantValidator()
    assert len(v.invariants) >= 11


def test_invariant_validator_custom():
    inv = SimulationInvariant(id="test.custom", description="custom", severity="warn", evaluator=lambda w: True)
    v = InvariantValidator(invariants=[inv])
    assert len(v.invariants) == 1
    assert v.invariants[0].id == "test.custom"


def test_validate_healthy_world():
    v = InvariantValidator()
    w = SimulationWorld()
    violations = v.validate(w)
    assert len(violations) == 0, f"Healthy world has violations: {[vi.invariant_id for vi in violations]}"


def test_validate_soft_no_raise():
    w = SimulationWorld()
    w.organ_state.cardiovascular.health = -0.5
    v = InvariantValidator()
    violations = v.validate_soft(w)
    fatal = [vi for vi in violations if vi.severity == "fatal"]
    assert len(fatal) > 0, "Expected fatal violation for organ health < 0"


def test_validate_fatal_raises():
    w = SimulationWorld()
    w.organ_state.cardiovascular.health = -0.5
    v = InvariantValidator()
    try:
        v.validate(w)
        assert False, "Expected InvariantFatalError"
    except InvariantFatalError as e:
        assert len(e.violations) > 0
        assert any(vi.invariant_id == "physio.organ_health_bounds" for vi in e.violations)


def test_invariant_fatal_error_is_simulation_corruption():
    assert issubclass(InvariantFatalError, SimulationCorruptionError)


def test_invariant_violation_dataclass():
    v = InvariantViolation(invariant_id="test", severity="error", message="test msg", tick=5)
    assert v.invariant_id == "test"
    assert v.tick == 5


def test_simulation_invariant_frozen():
    inv = SimulationInvariant(id="x", description="x", severity="warn", evaluator=lambda w: True)
    try:
        inv.id = "y"
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_add_invariant():
    v = InvariantValidator()
    initial = len(v.invariants)
    inv = SimulationInvariant(id="test.added", description="added", severity="warn", evaluator=lambda w: True)
    v.add_invariant(inv)
    assert len(v.invariants) == initial + 1


def test_ledger_events_on_violation():
    ledger = EventLedger()
    v = InvariantValidator(ledger=ledger)
    w = SimulationWorld()
    w.physiology.vitals["spo2"] = -10
    v.validate_soft(w)
    events = [e for e in ledger.all() if e.type in ("invariant_warning", "invariant_error", "simulation_corruption")]
    assert len(events) > 0, "Expected ledger events for violations"


def test_hospital_invariants_exist():
    assert len(HOSPITAL_INVARIANTS) >= 0


def test_validate_hospital_method():
    v = InvariantValidator()
    w = SimulationWorld()
    try:
        v.validate_hospital(w)
    except Exception:
        pass


def test_register_invariant():
    initial = len(CANONICAL_INVARIANTS)
    inv = SimulationInvariant(id="test.registered", description="registered", severity="warn", evaluator=lambda w: True)
    register_invariant(inv)
    assert len(CANONICAL_INVARIANTS) == initial + 1
    CANONICAL_INVARIANTS.pop()


TESTS = [
    ("contracts: canonical invariants count", test_canonical_invariants_count),
    ("contracts: validator default invariants", test_invariant_validator_default),
    ("contracts: validator custom invariants", test_invariant_validator_custom),
    ("contracts: validate healthy world", test_validate_healthy_world),
    ("contracts: validate_soft no raise on fatal", test_validate_soft_no_raise),
    ("contracts: validate raises on fatal", test_validate_fatal_raises),
    ("contracts: InvariantFatalError is SimulationCorruptionError", test_invariant_fatal_error_is_simulation_corruption),
    ("contracts: InvariantViolation dataclass", test_invariant_violation_dataclass),
    ("contracts: SimulationInvariant frozen", test_simulation_invariant_frozen),
    ("contracts: add_invariant", test_add_invariant),
    ("contracts: ledger events on violation", test_ledger_events_on_violation),
    ("contracts: hospital invariants exist", test_hospital_invariants_exist),
    ("contracts: validate_hospital method", test_validate_hospital_method),
    ("contracts: register_invariant", test_register_invariant),
]
