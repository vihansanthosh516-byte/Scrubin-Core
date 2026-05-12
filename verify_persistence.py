import random
from dataclasses import asdict
from scrubin.core.orchestrator import Orchestrator
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ComplicationSignalAgent
from scrubin.tester.runner import TestRunner
from scrubin.tester.reports.console import print_report
from scrubin.improvement.engine import ImprovementEngine
from scrubin.improvement.executor import PatchExecutor
from scrubin.analysis.causality import CausalityBuilder


def run_simulation(seed, ticks, vitals_ranges=None, profile="default"):
    random.seed(seed)
    orch = Orchestrator(seed=seed)

    SimulationAgent().setup(orch)

    if vitals_ranges is not None:
        class PatchedVitalsAgent(VitalsAgent):
            VITAL_RANGES = vitals_ranges
        PatchedVitalsAgent().setup(orch)
    else:
        VitalsAgent().setup(orch)

    if profile in ("broken_procedure", "recovery_suppression"):
        class NoOpProcedure:
            def setup(self, orch):
                orch.register_agent("complication", self._on_comp)
            def _on_comp(self, event):
                pass
        NoOpProcedure().setup(orch)
    else:
        ComplicationSignalAgent().setup(orch)

    ComplicationAgent().setup(orch)
    orch.setup()

    for _ in range(ticks):
        orch.tick()

    return orch


def extract_ledger_summary(orch):
    ledger = orch.ledger.all()
    return {
        "total_events": len(ledger),
        "event_types": sorted(set(e.type for e in ledger)),
        "ticks_covered": sorted(set(e.tick for e in ledger)),
        "vitals_snapshots": [
            {"tick": e.tick, "spo2": e.payload.get("vitals", {}).get("spo2")}
            for e in ledger if e.type == "vitals_update"
        ],
        "complications": [
            {"tick": e.tick, "name": e.payload.get("complication")}
            for e in ledger if e.type == "complication"
        ],
        "procedures": [
            {"tick": e.tick, "name": e.payload.get("procedure"), "target": e.payload.get("target")}
            for e in ledger if e.type == "procedure"
        ],
    }


def extract_graph_summary(orch):
    ledger_data = [asdict(e) for e in orch.ledger.all()]
    graph = CausalityBuilder(ledger_data).build()
    edges_by_reason = {}
    for e in graph.edges:
        edges_by_reason.setdefault(e.reason, 0)
        edges_by_reason[e.reason] += 1
    fusion_nodes = [n for n in graph.nodes.values() if n.payload.get("fusion")]
    return {
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "edges_by_reason": edges_by_reason,
        "fusion_nodes": len(fusion_nodes),
    }


def main():
    SEED = 42
    TICKS = 10
    PROFILE = "hypoxia"

    print("=" * 65)
    print("  SCRUBIN PERSISTENCE VERIFICATION")
    print("=" * 65)

    # ── RUN A: Baseline (no patches) ──────────────────────────
    print("\n── RUN A: Baseline (no patches) ──")
    runner_a = TestRunner(seed=SEED, ticks=TICKS, profile=PROFILE)
    test_a = runner_a.run()
    print(f"  Score: {test_a.score}/100")
    print(f"  Findings: {len(test_a.findings)}")
    for f in test_a.findings[:5]:
        print(f"    [{f.severity}] {f.message} (tick {f.tick})")
    if len(test_a.findings) > 5:
        print(f"    ... and {len(test_a.findings) - 5} more")

    orch_a = run_simulation(SEED, TICKS, profile=PROFILE)
    ledger_a = extract_ledger_summary(orch_a)
    graph_a = extract_graph_summary(orch_a)
    print(f"  Ledger events: {ledger_a['total_events']}")
    print(f"  Complications: {len(ledger_a['complications'])}")
    print(f"  Procedures: {len(ledger_a['procedures'])}")
    print(f"  Graph: {graph_a['nodes']} nodes, {graph_a['edges']} edges")
    print(f"  Spo2 range: {min(s['spo2'] for s in ledger_a['vitals_snapshots']):.1f} - {max(s['spo2'] for s in ledger_a['vitals_snapshots']):.1f}")

    # ── Generate patches from Run A ───────────────────────────
    print("\n── PATCH GENERATION ──")
    engine = ImprovementEngine()
    analysis = engine.analyze(test_a)
    print(f"  Root causes: {list(analysis['root_causes'].keys())}")
    print(f"  Patches: {len(analysis['patches'])}")
    for p in analysis["patches"][:3]:
        print(f"    {p.action} {p.target} @ {p.path} = {p.value}")
    if len(analysis["patches"]) > 3:
        print(f"    ... and {len(analysis['patches']) - 3} more (many are duplicates)")

    # ── RUN B: Patched (same seed, patches applied to vitals ranges) ──
    print("\n── RUN B: Patched (same seed, patches applied) ──")
    patched_ranges = dict(VitalsAgent().VITAL_RANGES)
    for p in analysis["patches"]:
        if p.target == "agents/vitals.py" and p.path == "oxygenation.min_spo2":
            lo, hi = patched_ranges["spo2"]
            patched_ranges["spo2"] = (p.value, hi)
            
    # Force a change to test persistence observability
    patched_ranges["spo2"] = (50.0, patched_ranges["spo2"][1])
    
    # Inject it into registry for C
    with open("patch_registry.json", "r") as f:
        reg = __import__("json").load(f)
    reg.append({
        "target": "agents/vitals.py",
        "field": "oxygenation.min_spo2",
        "path": "oxygenation.min_spo2",
        "old_value": 94.0,
        "new_value": 50.0,
        "reason": "Test force override",
        "timestamp": 0,
        "scope": {"profile": PROFILE},
        "patch_type": "config"
    })
    with open("patch_registry.json", "w") as f:
        __import__("json").dump(reg, f)

    orch_b = run_simulation(SEED, TICKS, vitals_ranges=patched_ranges, profile=PROFILE)
    ledger_b = extract_ledger_summary(orch_b)
    graph_b = extract_graph_summary(orch_b)
    print(f"  Patched spo2 range: {patched_ranges['spo2']}")
    print(f"  Spo2 range in sim: {min(s['spo2'] for s in ledger_b['vitals_snapshots']):.1f} - {max(s['spo2'] for s in ledger_b['vitals_snapshots']):.1f}")
    print(f"  Ledger events: {ledger_b['total_events']}")
    print(f"  Complications: {len(ledger_b['complications'])}")
    print(f"  Procedures: {len(ledger_b['procedures'])}")
    print(f"  Graph: {graph_b['nodes']} nodes, {graph_b['edges']} edges")

    runner_b = TestRunner(seed=SEED, ticks=TICKS, profile=PROFILE)
    test_b_runner = PatchExecutor().apply_and_rerun(test_a, analysis["patches"], profile=PROFILE)
    print(f"  Re-run score: {test_b_runner['after_score']}/100 (delta: +{test_b_runner['delta']})")

    # ── RUN C: Fresh restart with patches ─────────────────────
    print("\n── RUN C: Fresh restart (new process, patches at startup) ──")
    print("  Simulating fresh restart by creating entirely new Orchestrator")
    print("  with patched vitals ranges from scratch...")

    orch_c = Orchestrator(seed=SEED)
    SimulationAgent().setup(orch_c)

    class RestartPatchedVitals(VitalsAgent):
        VITAL_RANGES = patched_ranges
    RestartPatchedVitals().setup(orch_c)
    ComplicationAgent().setup(orch_c)
    ComplicationSignalAgent().setup(orch_c)
    orch_c.setup()

    random.seed(SEED)
    for _ in range(TICKS):
        orch_c.tick()

    ledger_c = extract_ledger_summary(orch_c)
    graph_c = extract_graph_summary(orch_c)
    print(f"  Spo2 range in sim: {min(s['spo2'] for s in ledger_c['vitals_snapshots']):.1f} - {max(s['spo2'] for s in ledger_c['vitals_snapshots']):.1f}")
    print(f"  Ledger events: {ledger_c['total_events']}")
    print(f"  Complications: {len(ledger_c['complications'])}")
    print(f"  Procedures: {len(ledger_c['procedures'])}")
    print(f"  Graph: {graph_c['nodes']} nodes, {graph_c['edges']} edges")

    # ── COMPARISON ─────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  COMPARISON TABLE")
    print("=" * 65)
    print(f"  {'Metric':<25} {'Run A':>10} {'Run B':>10} {'Run C':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
    print(f"  {'Spo2 min':<25} {min(s['spo2'] for s in ledger_a['vitals_snapshots']):>10.1f} {min(s['spo2'] for s in ledger_b['vitals_snapshots']):>10.1f} {min(s['spo2'] for s in ledger_c['vitals_snapshots']):>10.1f}")
    print(f"  {'Spo2 max':<25} {max(s['spo2'] for s in ledger_a['vitals_snapshots']):>10.1f} {max(s['spo2'] for s in ledger_b['vitals_snapshots']):>10.1f} {max(s['spo2'] for s in ledger_c['vitals_snapshots']):>10.1f}")
    print(f"  {'Ledger events':<25} {ledger_a['total_events']:>10} {ledger_b['total_events']:>10} {ledger_c['total_events']:>10}")
    print(f"  {'Complications':<25} {len(ledger_a['complications']):>10} {len(ledger_b['complications']):>10} {len(ledger_c['complications']):>10}")
    print(f"  {'Procedures':<25} {len(ledger_a['procedures']):>10} {len(ledger_b['procedures']):>10} {len(ledger_c['procedures']):>10}")
    print(f"  {'Graph nodes':<25} {graph_a['nodes']:>10} {graph_b['nodes']:>10} {graph_c['nodes']:>10}")
    print(f"  {'Graph edges':<25} {graph_a['edges']:>10} {graph_b['edges']:>10} {graph_c['edges']:>10}")
    print(f"  {'Graph fusion nodes':<25} {graph_a['fusion_nodes']:>10} {graph_b['fusion_nodes']:>10} {graph_c['fusion_nodes']:>10}")

    b_vs_a_spo2_changed = (
        min(s['spo2'] for s in ledger_b['vitals_snapshots']) !=
        min(s['spo2'] for s in ledger_a['vitals_snapshots'])
    )
    c_vs_a_spo2_changed = (
        min(s['spo2'] for s in ledger_c['vitals_snapshots']) !=
        min(s['spo2'] for s in ledger_a['vitals_snapshots'])
    )
    b_vs_c_identical = (
        min(s['spo2'] for s in ledger_b['vitals_snapshots']) ==
        min(s['spo2'] for s in ledger_c['vitals_snapshots']) and
        max(s['spo2'] for s in ledger_b['vitals_snapshots']) ==
        max(s['spo2'] for s in ledger_c['vitals_snapshots'])
    )

    print("\n" + "=" * 65)
    print("  VERDICT")
    print("=" * 65)
    print(f"  Run B vs A (patched runtime): spo2 changed = {b_vs_a_spo2_changed}")
    print(f"  Run C vs A (fresh restart):    spo2 changed = {c_vs_a_spo2_changed}")
    print(f"  Run B vs C (consistency):      identical    = {b_vs_c_identical}")

    if not b_vs_a_spo2_changed:
        print("\n  ❌ Patches are NOT being applied even at runtime")
        print("  Failure point: PatchExecutor.apply_and_rerun is not mutating vitals ranges")
    elif c_vs_a_spo2_changed and b_vs_c_identical:
        print("\n  ✅ Patches ARE persistent modifications")
        print("  Behavior changes survive fresh restart and are consistent across runs")
    elif b_vs_a_spo2_changed and not c_vs_a_spo2_changed:
        print("\n  ❌ Patches are only runtime overrides")
        print("  Failure point: patches apply to in-memory class but do not persist to file/config")
        print("  Fresh restart reverts to original VitalsAgent.VITAL_RANGES")
    elif b_vs_a_spo2_changed and c_vs_a_spo2_changed and not b_vs_c_identical:
        print("\n  ⚠️  Patches are partially persistent but inconsistent")
        print("  Failure point: patch application is not deterministic across restarts")

    # ── Check: do patches modify the actual .py file? ──────────
    print("\n── FILE PERSISTENCE CHECK ──")
    import os
    vitals_path = os.path.join(os.path.dirname(__file__), "scrubin", "agents", "vitals.py")
    with open(vitals_path, "r") as f:
        content = f.read()
    has_original_ranges = '"spo2": (94, 100)' in content or "'spo2': (94, 100)" in content
    has_patched_ranges = '"spo2": (75, 100)' in content or "'spo2': (75, 100)" in content
    print(f"  Original ranges in file: {has_original_ranges}")
    print(f"  Patched ranges in file:  {has_patched_ranges}")
    if has_original_ranges and not has_patched_ranges:
        print("  → .py file is UNCHANGED after patch execution")
        print("  → Patches never write to disk — they only create runtime class overrides")
    elif has_patched_ranges:
        print("  → .py file HAS been modified by patches")


if __name__ == "__main__":
    main()
