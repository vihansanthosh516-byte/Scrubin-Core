import hashlib
import json

from scrubin.core.ledger import EventLedger, LoggedEvent


def ledger_fingerprint(ledger: EventLedger) -> str:
    entries = []
    for e in ledger.all():
        entries.append({
            "id": e.id,
            "sequence_id": e.sequence_id,
            "type": e.type,
            "tick": e.tick,
            "payload": _canonical_payload(e.payload),
            "parent_id": e.parent_id,
        })
    blob = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def ledger_canonical_json(ledger: EventLedger) -> str:
    entries = []
    for e in ledger.all():
        entries.append({
            "id": e.id,
            "sequence_id": e.sequence_id,
            "type": e.type,
            "tick": e.tick,
            "payload": _canonical_payload(e.payload),
            "parent_id": e.parent_id,
        })
    return json.dumps(entries, sort_keys=True, separators=(",", ":"))


def verify_deterministic(ledger: EventLedger) -> list[str]:
    violations = []
    prev_sort_key = None
    for e in ledger.all():
        sort_key = (-getattr(e, "priority", 0), e.tick, e.sequence_id)
        if prev_sort_key is not None and sort_key < prev_sort_key:
            violations.append(
                f"Non-deterministic ordering: event id={e.id} "
                f"sort_key={sort_key} < previous={prev_sort_key}"
            )
        prev_sort_key = sort_key
    return violations


def replay_matches(original: EventLedger, replayed: EventLedger) -> tuple[bool, list[str]]:
    a = original.all()
    b = replayed.all()
    mismatches = []
    if len(a) != len(b):
        mismatches.append(f"Event count mismatch: original={len(a)} replayed={len(b)}")
    for i, (oa, ob) in enumerate(zip(a, b)):
        if oa.type != ob.type:
            mismatches.append(f"Event {i}: type mismatch original={oa.type} replayed={ob.type}")
        if oa.tick != ob.tick:
            mismatches.append(f"Event {i}: tick mismatch original={oa.tick} replayed={ob.tick}")
        if oa.sequence_id != ob.sequence_id:
            mismatches.append(f"Event {i}: sequence_id mismatch original={oa.sequence_id} replayed={ob.sequence_id}")
        if _canonical_payload(oa.payload) != _canonical_payload(ob.payload):
            mismatches.append(f"Event {i}: payload mismatch")
    return len(mismatches) == 0, mismatches


def _canonical_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    cleaned = {}
    for k in sorted(payload.keys()):
        v = payload[k]
        if isinstance(v, dict):
            cleaned[k] = _canonical_payload(v)
        elif isinstance(v, float):
            cleaned[k] = round(v, 6)
        else:
            cleaned[k] = v
    return cleaned
