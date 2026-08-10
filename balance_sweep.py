"""Full-coverage balance sweep: runs perfect play + neglect on ALL 31 procedures
so every surgery's deterioration behavior is verified, not just a sample.

Prints a per-procedure table plus summary by risk tier, and flags any
procedure where perfect play dies or where behavior diverges from its tier.
"""
from scrubin_core_engine import SimulationOrchestrator
from scrubin_core_procedures import ALL_PROCEDURES

STEP_CAP = 60
SEEDS = [7, 42, 123, 999]


def _correct_option(decision, active_comp):
    for opt in decision.get("options", []):
        if active_comp in (opt.get("correctForComplications") or []):
            return opt["id"]
    for opt in decision.get("options", []):
        if opt.get("correctForComplications"):
            return opt["id"]
    return None


def perfect_run(seed, proc):
    orch = SimulationOrchestrator(seed, proc)
    crises = 0
    for _ in range(STEP_CAP):
        if orch.completed:
            break
        if orch.mode == "branched":
            d = orch.pending_decision
            if not d:
                orch.next()
                continue
            opt = _correct_option(d, orch.active_complication)
            if opt is None:
                return {"survived": False, "crises": crises, "why": "no rescue option"}
            orch.submit_decision(d["id"], opt)
            crises += 1
            continue
        orch.next()
    v = orch.vitals_engine.snapshot()
    return {
        "survived": orch.mode != "deceased",
        "crises": crises,
        "bp": round(v.get("bp_systolic", 0), 1),
        "spo2": round(v.get("spo2", 0), 1),
        "hr": round(v.get("heart_rate", 0), 1),
    }


def neglect_run(seed, proc):
    orch = SimulationOrchestrator(seed, proc)
    for _ in range(STEP_CAP):
        if orch.completed:
            break
        if orch.mode == "branched":
            for _p in range(12):
                if orch.completed:
                    break
                orch.tick_vitals_only()
            continue
        orch.next()
    return {
        "survived": orch.mode != "deceased",
        "died_at_tick": orch._tick if orch.mode == "deceased" else None,
    }


def tier_of(proc):
    return proc["initialState"]["riskProfile"].get("deterioration_rate", 1.0)


TIER_LABEL = {0.45: "low", 0.8: "moderate", 1.6: "high", 2.0: "critical"}


def main():
    problems = []
    info = []
    print(f"{'procedure':<26s} {'tier':<9s} crises  bp_min spo2_min  perfect  neglect")
    print("-" * 95)
    per_tier = {}
    for p in ALL_PROCEDURES:
        pid = p["id"]
        rate = tier_of(p)
        tier = TIER_LABEL.get(rate, f"rate={rate}")
        per_tier.setdefault(tier, []).append(pid)
        p_crises, p_bp, p_spo2 = [], [], []
        neg_survived = 0
        for s in SEEDS:
            pr = perfect_run(s, pid)
            p_crises.append(pr["crises"])
            p_bp.append(pr["bp"])
            p_spo2.append(pr["spo2"])
            if not pr["survived"]:
                problems.append(f"{pid}: PERFECT PLAY died (seed {s})")
            if neglect_run(s, pid)["survived"]:
                neg_survived += 1

        # Per-tier neglect expectations:
        #   low:      healthy outpatient patients tolerate standard care -> survival OK
        #   moderate: stakes should exist in most seeds -> flag if NEVER lethal
        #   high:     neglect should kill in MOST seeds -> flag if < 3/4 die
        #   critical: neglect must kill -> flag if ANY survive
        neg_flag = ""
        if tier == "high" and neg_survived >= 3:
            neg_flag = "  <<< NEGLECT TOO TOLERANT (high tier)"
            problems.append(f"{pid}: high tier but neglect survives {neg_survived}/4 seeds")
        elif tier == "critical" and neg_survived > 0:
            neg_flag = "  <<< NEGLECT SURVIVES (critical)"
            problems.append(f"{pid}: critical tier but neglect survives {neg_survived}/4 seeds")
        elif tier == "moderate" and neg_survived == 4:
            neg_flag = "  (never develops a crisis under neglect)"
            info.append(f"{pid}: moderate but no crisis ever develops (neglect safe)")

        print(f"{pid:<26s} {tier:<9s} {min(p_crises):>2}-{max(p_crises):<3d} "
              f"{min(p_bp):>6.1f} {min(p_spo2):>6.1f}  {'OK' if not problems or problems[-1].startswith(pid) else '':<7s}"
              f"{'OK' if neg_survived < 4 else f'{neg_survived}/4 survive':<15s}{neg_flag}")

    print("\n=== BY TIER (perfect play) ===")
    for tier, procs in per_tier.items():
        all_c = []
        for pid in procs:
            for s in SEEDS:
                all_c.append(perfect_run(s, pid)["crises"])
        print(f"{tier:9s} {len(procs):>2} procedures  crises {min(all_c)}-{max(all_c)} "
              f"(avg {sum(all_c)/len(all_c):.1f})")

    if problems:
        print("\n⚠️ REQUIRES ATTENTION:")
        for pr in problems:
            print("  -", pr)
    else:
        print("\n✅ ALL 31 PROCEDURES: perfect play survives everywhere; tier expectations met")
    if info:
        print("\nℹ️ Gentle-by-physiology (no crisis under neglect, but not failures):")
        for i in info:
            print("  -", i)


if __name__ == "__main__":
    main()
