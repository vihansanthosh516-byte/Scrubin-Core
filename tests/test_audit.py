from scrubin.core.ledger import EventLedger
from scrubin.audit.transitions import TransitionAuditor, StateTransition, _compute_delta


def test_compute_delta_changed():
    delta = _compute_delta({"a": 1, "b": 2}, {"a": 1, "b": 3})
    assert "a" not in delta
    assert delta["b"] == {"before": 2, "after": 3}


def test_compute_delta_added_key():
    delta = _compute_delta({"a": 1}, {"a": 1, "b": 2})
    assert delta["b"] == {"before": None, "after": 2}


def test_compute_delta_removed_key():
    delta = _compute_delta({"a": 1, "b": 2}, {"a": 1})
    assert delta["b"] == {"before": 2, "after": None}


def test_compute_delta_no_change():
    delta = _compute_delta({"a": 1}, {"a": 1})
    assert len(delta) == 0


def test_transition_auditor_record():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    t = auditor.record(tick=1, source_event="test", affected_system="sys", before={"x": 1}, after={"x": 2})
    assert t.tick == 1
    assert t.delta == {"x": {"before": 1, "after": 2}}
    assert auditor.count == 1


def test_transition_auditor_for_tick():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    auditor.record(tick=1, source_event="e1", affected_system="s1", before={}, after={})
    auditor.record(tick=2, source_event="e2", affected_system="s2", before={}, after={})
    auditor.record(tick=1, source_event="e3", affected_system="s3", before={}, after={})
    result = auditor.transitions_for_tick(1)
    assert len(result) == 2


def test_transition_auditor_for_system():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    auditor.record(tick=1, source_event="e1", affected_system="cardio", before={}, after={})
    auditor.record(tick=2, source_event="e2", affected_system="neuro", before={}, after={})
    result = auditor.transitions_for_system("cardio")
    assert len(result) == 1


def test_transition_auditor_all():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    auditor.record(tick=1, source_event="e1", affected_system="s1", before={}, after={})
    auditor.record(tick=2, source_event="e2", affected_system="s2", before={}, after={})
    assert len(auditor.all_transitions()) == 2


def test_transition_auditor_clear():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    auditor.record(tick=1, source_event="e1", affected_system="s1", before={}, after={})
    auditor.clear()
    assert auditor.count == 0


def test_transition_auditor_ledger_event():
    ledger = EventLedger()
    auditor = TransitionAuditor(ledger=ledger)
    auditor.record(tick=1, source_event="evolve", affected_system="world", before={"x": 1}, after={"x": 2})
    events = [e for e in ledger.all() if e.type == "state_transition_audit"]
    assert len(events) == 1


def test_state_transition_dataclass():
    t = StateTransition(tick=5, source_event="e", affected_system="s", before={}, after={}, delta={})
    assert t.tick == 5


TESTS = [
    ("audit: compute delta changed key", test_compute_delta_changed),
    ("audit: compute delta added key", test_compute_delta_added_key),
    ("audit: compute delta removed key", test_compute_delta_removed_key),
    ("audit: compute delta no change", test_compute_delta_no_change),
    ("audit: record transition", test_transition_auditor_record),
    ("audit: transitions for tick", test_transition_auditor_for_tick),
    ("audit: transitions for system", test_transition_auditor_for_system),
    ("audit: all transitions", test_transition_auditor_all),
    ("audit: clear transitions", test_transition_auditor_clear),
    ("audit: ledger event on record", test_transition_auditor_ledger_event),
    ("audit: StateTransition dataclass", test_state_transition_dataclass),
]
