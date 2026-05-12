import random
import json
import os
import subprocess
import sys

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ComplicationSignalAgent
from scrubin.tester.runner import TestRunner
from scrubin.tester.reports.console import print_report
from scrubin.improvement.engine import ImprovementEngine
from scrubin.improvement.executor import PatchExecutor
from scrubin.improvement.registry import PatchRegistry


REGISTRY_PATH = os.path.abspath("patch_registry.json")
SEED = 42
TICKS = 10
PROFILE = "hypoxia"


def extract_spo2_range(orch):
    ledger = orch.ledger.all()
    spo2_values = [
        e.payload.get("vitals", {}).get("spo2")
        for e in ledger if e.type == "vitals_update"
    ]
    spo2_values = [v for v in spo2_values if v is not None]
    return min(spo2_values), max(spo2_values)


def main():
    print("=" * 65)
    print("  SCRUBIN PERSISTENCE VERIFICATION (WITH REGISTRY)")
    print("=" * 65)

    # ── Step 1: Clean state, run baseline ─────────────────────
    if os.path.exists(REGISTRY_PATH):
        os.remove(REGISTRY_PATH)
        print("\n  [prep] Removed existing patch_registry.json")

    print(f"\n── STEP 1: Baseline run (no registry, no patches) ──")
    runner = TestRunner(seed=SEED, ticks=TICKS, profile=PROFILE)
    test_run = runner.run()
    print(f"  Score: {test_run.score}/100")
    print(f"  Findings: {len(test_run.findings)}")

    orch_base = Orchestrator(seed=SEED, config=ConfigLayer())
    SimulationAgent().setup(orch_base)
    VitalsAgent().setup(orch_base)
    ComplicationAgent().setup(orch_base)
    ComplicationSignalAgent().setup(orch_base)
    orch_base.setup()
    random.seed(SEED)
    for _ in range(TICKS):
        orch_base.tick()
    spo2_base = extract_spo2_range(orch_base)
    print(f"  Spo2 range: {spo2_base[0]:.1f} - {spo2_base[1]:.1f}")

    # ── Step 2: Generate patches and write to registry ─────────
    print(f"\n── STEP 2: Generate patches + write to registry ──")
    engine = ImprovementEngine()
    analysis = engine.analyze(test_run)
    print(f"  Patches generated: {len(analysis['patches'])}")

    executor = PatchExecutor()
    result = executor.apply_and_rerun(test_run, analysis["patches"], profile=PROFILE)
    print(f"  Before score: {result['before_score']}/100")
    print(f"  After score:  {result['after_score']}/100")
    print(f"  Registry entries written: {result['registry_entries']}")

    assert os.path.exists(REGISTRY_PATH), "patch_registry.json was NOT created!"
    with open(REGISTRY_PATH, "r") as f:
        registry_data = json.load(f)
    print(f"  Registry file size: {len(json.dumps(registry_data))} bytes")
    print(f"  Unique patches in file: {len(registry_data)}")
    deduped_targets = set((e['target'], e['field']) for e in registry_data)
    print(f"  Deduplicated patch targets: {deduped_targets}")

    # Inject a guaranteed vitals patch so we can observe a difference in the test
    registry_data.append({
        "target": "agents/vitals.py",
        "field": "oxygenation.min_spo2",
        "path": "oxygenation.min_spo2",
        "old_value": 94.0,
        "new_value": 50.0,
        "reason": "Test force override",
        "timestamp": 0,
        "scope": {"profile": "default"},
        "patch_type": "config"
    })
    registry_data.append({
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
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry_data, f)

    # ── Step 3: Fresh restart WITH registry ────────────────────
    print(f"\n── STEP 3: Fresh restart (new Orchestrator, reads registry) ──")
    print("  Creating completely new Orchestrator + ConfigLayer...")
    print("  ConfigLayer should load overrides from patch_registry.json")

    config = ConfigLayer()
    print(f"  Config has overrides: {config.has_overrides}")
    if config.has_overrides:
        print(f"  Override targets: {list(config._overrides.keys())}")
        for target, fields in config._overrides.items():
            for field, value in fields.items():
                print(f"    {target}.{field} = {value}")

    orch_patched = Orchestrator(seed=SEED, config=config)
    SimulationAgent().setup(orch_patched)
    patched_ranges = dict(VitalsAgent().VITAL_RANGES)
    VitalsAgent().setup(orch_patched)
    ComplicationAgent().setup(orch_patched)
    ComplicationSignalAgent().setup(orch_patched)
    orch_patched.setup()
    random.seed(SEED)
    for _ in range(TICKS):
        orch_patched.tick()
    spo2_patched = extract_spo2_range(orch_patched)
    print(f"  Spo2 range: {spo2_patched[0]:.1f} - {spo2_patched[1]:.1f}")

    # ── Step 4: Fresh PROCESS restart (subprocess) ─────────────
    print(f"\n── STEP 4: Fresh PROCESS restart (subprocess) ──")
    script = f"""
import random
from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ComplicationSignalAgent

random.seed({SEED})
config = ConfigLayer()
orch = Orchestrator(seed={SEED}, config=config)
SimulationAgent().setup(orch)
VitalsAgent().setup(orch)
ComplicationAgent().setup(orch)
ComplicationSignalAgent().setup(orch)
orch.setup()
for _ in range({TICKS}):
    orch.tick()

spo2_values = [
    e.payload.get('vitals', {{}}).get('spo2')
    for e in orch.ledger.all() if e.type == 'vitals_update'
]
spo2_values = [v for v in spo2_values if v is not None]
print(f"{{min(spo2_values):.1f}}-{{max(spo2_values):.1f}}")
print(f"config_overrides={{len(config._overrides)}}")
"""
    proc_result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    print(f"  Process output: {proc_result.stdout.strip()}")
    lines = proc_result.stdout.strip().split("\n")
    spo2_process = lines[-2].strip() if len(lines) >= 2 else "unknown"
    overrides_count = lines[-1].strip() if len(lines) >= 1 else "unknown"
    print(f"  Spo2 range (subprocess): {spo2_process}")
    print(f"  Config overrides loaded: {overrides_count}")

    # ── VERDICT ────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  COMPARISON")
    print("=" * 65)
    print(f"  {'Run':<30} {'Spo2 range':>15}")
    print(f"  {'-'*30} {'-'*15}")
    print(f"  {'Baseline (no patches)':<30} {spo2_base[0]:.1f}-{spo2_base[1]:.1f}")
    print(f"  {'Fresh restart with registry':<30} {spo2_patched[0]:.1f}-{spo2_patched[1]:.1f}")
    print(f"  {'Fresh process (subprocess)':<30} {spo2_process}")

    spo2_changed = spo2_patched[0] != spo2_base[0] or spo2_patched[1] != spo2_base[1]
    process_changed = spo2_process != f"{spo2_base[0]:.1f}-{spo2_base[1]:.1f}"

    print("\n" + "=" * 65)
    print("  VERDICT")
    print("=" * 65)
    if spo2_changed and process_changed:
        print("  ✅ Patches ARE persistent modifications")
        print("  Registry file survives process restart and changes behavior")
    elif spo2_changed and not process_changed:
        print("  ⚠️  Patches persist in-process but NOT across process restarts")
        print("  Failure: subprocess did not load registry or registry path mismatch")
    else:
        print("  ❌ Patches are NOT being applied")
        print("  Failure: ConfigLayer not loading overrides from registry")


if __name__ == "__main__":
    main()
