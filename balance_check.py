"""Balance harness: verifies deterioration is gentler for low-risk (beginner)
surgeries and brutal for high/critical (advanced) ones.

- perfect_run: answer stock steps via next(), rescue every spontaneous
  complication with the clinically-correct intervention.
- neglect_run: never rescue; only advance steps, letting vitals spiral.
"""
import random
from scrubin_core_engine import SimulationOrchestrator

RISK_PROCEDURES = {
    "low": ["inguinal-hernia", "thyroidectomy", "carpal-tunnel-release"],
    "moderate": ["appendectomy", "cholecystectomy", "sigmoid-colectomy"],
    "high": ["cabg", "craniotomy", "pulmonary-lobectomy"],
    "critical": ["exploratory-laparotomy", "whipple", "aaa-repair"],
}

STEP_CAP = 60  # stock steps per case (banks are 30-40, engine adds margin)


def _correct_option(decision, active_comp):
    for opt in decision.get("options", []):
        treats = opt.get("correctForComplications") or []
        if active_comp in treats:
            return opt["id"]
    # fallback: first option that lists anything (engine always marks one)
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
                # should not happen; bail to avoid infinite loop
                return {"survived": False, "crises": crises, "why": "no rescue option"}
            orch.submit_decision(d["id"], opt)
            crises += 1
            continue
        orch.next()
    v = orch.vitals_engine.snapshot()
    return {
        "survived": orch.mode != "deceased",
        "crises": crises,
        "final_bp": round(v.get("bp_systolic", 0), 1),
        "final_spo2": round(v.get("spo2", 0), 1),
        "final_hr": round(v.get("heart_rate", 0), 1),
        "tick": orch._tick,
        "mode": orch.mode,
    }


def neglect_run(seed, proc, polls_between=12):
    """Advance steps but never rescue; in branched mode, tick via the poll path
    (as the real client does) so the untended patient's vitals decay and can
    cross lethal thresholds."""
    orch = SimulationOrchestrator(seed, proc)
    for _ in range(STEP_CAP):
        if orch.completed:
            break
        if orch.mode == "branched":
            for _p in range(polls_between):
                if orch.completed:
                    break
                orch.tick_vitals_only()
            continue
        orch.next()
    v = orch.vitals_engine.snapshot()
    return {
        "survived": orch.mode != "deceased",
        "died_at_tick": orch._tick if orch.mode == "deceased" else None,
        "final_bp": round(v.get("bp_systolic", 0), 1),
    }


def main():
    seeds = [7, 42, 123, 999]
    print("=== PERFECT PLAY ===")
    for level, procs in RISK_PROCEDURES.items():
        rows = []
        for p in procs:
            for s in seeds:
                r = perfect_run(s, p)
                rows.append(r)
        crises = [r["crises"] for r in rows]
        deaths = sum(1 for r in rows if not r["survived"])
        bp = [r["final_bp"] for r in rows]
        print(f"{level:9s} n={len(rows):2d} deaths={deaths} crises={min(crises)}-{max(crises)} "
              f"(avg {sum(crises)/len(crises):.1f}) finalBP {min(bp)}-{max(bp)}")

    print("\n=== NEGLECT (ignore crises) ===")
    for level, procs in RISK_PROCEDURES.items():
        rows = []
        for p in procs:
            for s in seeds:
                rows.append(neglect_run(s, p))
        deaths = sum(1 for r in rows if not r["survived"])
        died_ticks = [r["died_at_tick"] for r in rows if r["died_at_tick"]]
        t = f"death@{min(died_ticks)}-{max(died_ticks)} ticks" if died_ticks else "no deaths"
        print(f"{level:9s} n={len(rows):2d} deaths={deaths}/{len(rows)} {t}")


if __name__ == "__main__":
    main()
