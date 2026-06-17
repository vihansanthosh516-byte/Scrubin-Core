"""Meta‑orchestration deterministic hashing tests.

Ensures that two identical meta snapshots produce identical deterministic hashes.
"""

from __future__ import annotations

from dataclasses import replace

from scrubin.meta.models import (
    SystemConsistencyReport,
    DeterministicInvariantCheck,
    OrchestrationPlan,
    ExecutionTrace,
    MetaSnapshot,
)

def build_meta_snapshot() -> MetaSnapshot:
    consistency = SystemConsistencyReport(violations=("error1", "error2"))
    invariant = DeterministicInvariantCheck(issues=("issue1",))
    plan = OrchestrationPlan()
    trace = ExecutionTrace()
    return MetaSnapshot(
        state=None,
        consistency_report=consistency,
        invariant_check=invariant,
        orchestration_plan=plan,
        execution_trace=trace,
    )

def test_meta_snapshot_hash_stability():
    snap1 = build_meta_snapshot()
    snap2 = build_meta_snapshot()
    assert snap1.deterministic_hash == snap2.deterministic_hash

def test_meta_snapshot_replace_updates_hash():
    snap = build_meta_snapshot()
    new_snap = replace(snap, state="new_state")
    assert new_snap.deterministic_hash != snap.deterministic_hash
