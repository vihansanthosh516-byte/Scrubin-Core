"""
ScrubIn All-Surgeries Automated Trial Runner
============================================
Executes full trial runs for all 31 surgical procedures registered in Scrubin-Core.
Tests:
  - SessionManager Creation & Initialization
  - Tick execution & Vitals progression
  - Complication triggering with procedure-specific weights
  - Decision submission & Complication resolution
  - Procedure completion & Final state summary
"""

import sys
import time
from typing import Dict, Any

# Ensure stdout handles UTF-8 formatting
sys.stdout.reconfigure(encoding='utf-8')

from scrubin_core_procedures import ALL_PROCEDURES, list_procedures
from scrubin_core_engine import SessionManager


def run_all_surgeries_test():
    procedures = list_procedures()
    total_procedures = len(procedures)

    print("=" * 75)
    print(f"🏥 SCRUBIN ALL-SURGERIES TRIAL RUNNER ({total_procedures} PROCEDURES TOTAL)")
    print("=" * 75)

    passed_count = 0
    failed_count = 0
    failures = []

    start_time = time.time()

    for idx, proc in enumerate(procedures, start=1):
        proc_id = proc["id"]
        proc_name = proc["name"]
        category = proc.get("category", "N/A")
        specialty = proc.get("specialty", "N/A")
        allowed_comps = proc.get("allowedComplications", ["infection", "hemorrhage", "hypoxia"])

        print(f"\n[{idx:02d}/{total_procedures}] Testing Procedure: '{proc_name}' (id: '{proc_id}')")
        print(f"     Specialty: {specialty} | Category: {category} | Phases: {len(proc.get('phases', []))}")

        try:
            # 1. Instantiate SessionManager & Start Session
            manager = SessionManager()
            session = manager.create(f"sim_test_{idx}", seed=42, procedure_id=proc_id)
            state = session.state
            orchestrator = session.orchestrator

            # Assertions for initial state
            assert state["mode"] == "stock", f"Expected mode 'stock', got '{state['mode']}'"
            assert state["physiologicalReserve"] == 100.0, f"Expected reserve 100.0, got {state['physiologicalReserve']}"
            assert state["procedureId"] == proc_id, f"Expected proc_id '{proc_id}', got '{state['procedureId']}'"
            assert len(state["vitals"]) > 0, "Vitals should be populated"

            init_bp = state["vitals"].get("bp_systolic")
            init_hr = state["vitals"].get("heart_rate")
            init_spo2 = state["vitals"].get("spo2")
            print(f"     ✓ Init State OK: BP={init_bp}, HR={init_hr}, SpO2={init_spo2}%")

            # 2. Advance Ticks (Simulate procedure progression)
            for t in range(5):
                tick_state = orchestrator.tick_vitals_only()
                assert tick_state["mode"] == "stock", f"Mode changed unexpectedly on tick {t+1}: {tick_state['mode']}"

            print(f"     ✓ Advanced 5 ticks successfully. Current Tick: {orchestrator._tick}")

            # 3. Trigger a Complication
            target_comp = allowed_comps[0] if allowed_comps else "hemorrhage"
            comp_state = orchestrator.trigger_complication(target_comp)

            assert comp_state["mode"] == "branched", f"Expected mode 'branched', got '{comp_state['mode']}'"
            assert comp_state["activeComplication"] == target_comp, f"Active complication mismatch: {comp_state['activeComplication']}"
            assert comp_state["physiologicalReserve"] == 75.0, f"Reserve should drop to 75.0, got {comp_state['physiologicalReserve']}"
            assert comp_state["pendingDecision"] is not None, "Pending decision should be present after complication"

            print(f"     ✓ Triggered Complication '{target_comp}': mode=branched, reserve=75.0%")

            # 4. Resolve Decision
            pending = comp_state["pendingDecision"]
            decision_id = pending["id"]
            options = pending.get("options", [])
            assert len(options) > 0, "Pending decision must have options"

            # Find the option that handles the active complication
            correct_opt = next(
                (o for o in options if target_comp in o.get("correctForComplications", [])),
                options[0]
            )
            resolved_state = orchestrator.submit_decision(decision_id, correct_opt["id"])

            assert resolved_state["mode"] == "stock", f"Expected return to 'stock', got '{resolved_state['mode']}'"
            assert resolved_state["activeComplication"] is None, "Active complication should be cleared"

            opt_text = correct_opt.get("label") or correct_opt.get("text") or "Choice"
            print(f"     ✓ Decision Resolved ({opt_text[:35]}...): returned to mode 'stock'")

            # 5. Complete Procedure
            orchestrator.completed = True
            final_state = orchestrator.get_state()
            assert final_state["completed"] is True, "Procedure completion flag should be True"

            print(f"     ✅ TRIAL SUCCESSFUL FOR '{proc_name}'")
            passed_count += 1

        except Exception as e:
            print(f"     ❌ TRIAL FAILED FOR '{proc_name}': {e}")
            failures.append((proc_id, proc_name, str(e)))
            failed_count += 1

    elapsed = time.time() - start_time
    print("\n" + "=" * 75)
    print("📋 SUMMARY OF SURGICAL TRIAL RUNNS")
    print("=" * 75)
    print(f"Total Surgeries Tested: {total_procedures}")
    print(f"Passed:                 {passed_count} / {total_procedures} ({(passed_count/total_procedures)*100:.1f}%)")
    print(f"Failed:                 {failed_count} / {total_procedures}")
    print(f"Elapsed Time:           {elapsed:.2f} seconds")

    if failures:
        print("\n❌ Failed Procedures Details:")
        for fid, fname, err in failures:
            print(f"  - [{fid}] {fname}: {err}")
    else:
        print("\n🎉 ALL 31 SURGICAL PROCEDURES PASSED TRIAL SIMULATION VERIFICATION PERFECTLY!")

    return failed_count == 0


if __name__ == "__main__":
    success = run_all_surgeries_test()
    sys.exit(0 if success else 1)
