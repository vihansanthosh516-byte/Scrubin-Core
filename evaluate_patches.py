import random
import json
import os
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
from scrubin.tester.models import TestFinding


SEEDS = [1, 7, 42, 99, 123]
PROFILES = ["default", "hypoxia", "broken_procedure", "recovery_suppression", "causality_race"]
TICKS = 10
REGISTRY_PATH = os.path.abspath("patch_registry.json")


def run_baseline(seed, profile):
    runner = TestRunner(seed=seed, ticks=TICKS, profile=profile)
    return runner.run()


def run_patched(seed, profile):
    runner = TestRunner(seed=seed, ticks=TICKS, profile=profile)
    return runner.run()


def finding_summary(findings):
    errors = [f for f in findings if f.severity == "error"]
    warns = [f for f in findings if f.severity == "warn"]
    return {"errors": len(errors), "warns": len(warns), "total": len(findings)}


def main():
    print("=" * 75)
    print("  SCRUBIN PATCH GENERALIZATION & REGRESSION EVALUATION")
    print("=" * 75)

    # ── Phase 1: Baseline runs (clean registry) ────────────────
    if os.path.exists(REGISTRY_PATH):
        os.remove(REGISTRY_PATH)

    print("\n── PHASE 1: Baseline runs (no patches) ──")
    baseline_results = {}

    for seed in SEEDS:
        for profile in PROFILES:
            key = (seed, profile)
            result = run_baseline(seed, profile)
            baseline_results[key] = {
                "score": result.score,
                "findings": finding_summary(result.findings),
                "finding_messages": [f.message for f in result.findings],
            }
            status = "✓" if result.score >= 80 else "✗" if result.score < 50 else "△"
            print(f"  seed={seed:>3} profile={profile:<22} score={result.score:>3}/100 {status}")

    # ── Phase 2: Generate patches per seed across ALL stress profiles ─
    print("\n── Phase 2: Generate patches per seed (all stress profiles) ──")
    all_patches_per_seed = {}

    for seed in SEEDS:
        if os.path.exists(REGISTRY_PATH):
            os.remove(REGISTRY_PATH)

        seed_patches = []
        for profile in PROFILES:
            if profile == "default":
                continue
            runner = TestRunner(seed=seed, ticks=TICKS, profile=profile)
            test_run = runner.run()
            engine = ImprovementEngine()
            analysis = engine.analyze(test_run, profile=profile)

            for p in analysis["patches"]:
                seed_patches.append(p)

        deduped = {}
        for p in seed_patches:
            val_key = str(p.value) if not isinstance(p.value, (int, float, str, bool)) else p.value
            scope_key = p.scope.get("profile", "default")
            deduped[(p.target, p.path, val_key, scope_key)] = p
        unique_patches = list(deduped.values())
        all_patches_per_seed[seed] = unique_patches

        print(f"  seed={seed:>3}: {len(seed_patches)} raw patches → {len(unique_patches)} unique")
        for p in unique_patches:
            print(f"    {p.action} {p.target} @ {p.path} = {p.value} scope={p.scope}")

    # ── Phase 3: Merge patches into unified registry ───────────
    print("\n── PHASE 3: Build unified patch registry (best-of) ──")
    if os.path.exists(REGISTRY_PATH):
        os.remove(REGISTRY_PATH)

    merged = {}
    for seed, patches in all_patches_per_seed.items():
        for p in patches:
            scope_key = p.scope.get("profile", "default")
            key = (p.target, p.path, scope_key)
            if key not in merged:
                merged[key] = {"patch": p, "seeds": [seed]}
            else:
                merged[key]["seeds"].append(seed)

        registry = PatchRegistry()
        for key, info in merged.items():
            p = info["patch"]
            registry.record(
                target=p.target,
                field=p.path,
                new_value=p.value,
                reason=f"{p.reason} (from seeds: {info['seeds']})",
                scope=p.scope,
                priority=p.priority,
            )

    print(f"  Unified registry: {len(registry.entries)} entries")
    for entry in registry.entries:
        print(f"    {entry['target']} @ {entry['field']} = {entry['new_value']}")

    # ── Phase 4: Patched runs across ALL seeds and profiles ────
    print("\n── PHASE 4: Patched runs (with unified registry) ──")
    patched_results = {}

    for seed in SEEDS:
        for profile in PROFILES:
            key = (seed, profile)
            result = run_patched(seed, profile)
            patched_results[key] = {
                "score": result.score,
                "findings": finding_summary(result.findings),
                "finding_messages": [f.message for f in result.findings],
            }
            base = baseline_results[key]["score"]
            delta = result.score - base
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            print(f"  seed={seed:>3} profile={profile:<22} score={result.score:>3}/100 (base={base} {arrow}{delta:+d})")

    # ── Phase 5: Analysis ──────────────────────────────────────
    print("\n" + "=" * 75)
    print("  ANALYSIS")
    print("=" * 75)

    # Per-profile score comparison
    print("\n── Score comparison by profile ──")
    print(f"  {'Profile':<22} {'Base avg':>8} {'Patched avg':>11} {'Delta':>7} {'Regressions':>12}")
    print(f"  {'-'*22} {'-'*8} {'-'*11} {'-'*7} {'-'*12}")

    profile_stability = {}
    for profile in PROFILES:
        base_scores = [baseline_results[(s, profile)]["score"] for s in SEEDS]
        patched_scores = [patched_results[(s, profile)]["score"] for s in SEEDS]
        deltas = [p - b for b, p in zip(base_scores, patched_scores)]
        regressions = sum(1 for d in deltas if d < 0)
        avg_base = sum(base_scores) / len(base_scores)
        avg_patched = sum(patched_scores) / len(patched_scores)
        avg_delta = avg_patched - avg_base
        profile_stability[profile] = {
            "avg_base": avg_base,
            "avg_patched": avg_patched,
            "avg_delta": avg_delta,
            "regressions": regressions,
            "min_delta": min(deltas),
            "max_delta": max(deltas),
        }
        reg_str = f"{regressions}/{len(SEEDS)}" if regressions > 0 else "0"
        print(f"  {profile:<22} {avg_base:>8.1f} {avg_patched:>11.1f} {avg_delta:>+7.1f} {reg_str:>12}")

    # Per-seed score comparison
    print("\n── Score comparison by seed ──")
    print(f"  {'Seed':>5} {'Base avg':>8} {'Patched avg':>11} {'Delta':>7} {'Regressions':>12}")
    print(f"  {'-'*5} {'-'*8} {'-'*11} {'-'*7} {'-'*12}")

    for seed in SEEDS:
        base_scores = [baseline_results[(seed, p)]["score"] for p in PROFILES]
        patched_scores = [patched_results[(seed, p)]["score"] for p in PROFILES]
        deltas = [p - b for b, p in zip(base_scores, patched_scores)]
        regressions = sum(1 for d in deltas if d < 0)
        avg_base = sum(base_scores) / len(base_scores)
        avg_patched = sum(patched_scores) / len(patched_scores)
        avg_delta = avg_patched - avg_base
        reg_str = f"{regressions}/{len(PROFILES)}" if regressions > 0 else "0"
        print(f"  {seed:>5} {avg_base:>8.1f} {avg_patched:>11.1f} {avg_delta:>+7.1f} {reg_str:>12}")

    # Patch effectiveness ranking
    print("\n── Patch effectiveness ranking ──")
    print(f"  {'Target':<25} {'Field':<25} {'Scope':<22} {'Value':>8} {'Seeds':>6} {'Robust':>8}")
    print(f"  {'-'*25} {'-'*25} {'-'*22} {'-'*8} {'-'*6} {'-'*8}")

    for key, info in sorted(merged.items(), key=lambda x: -len(x[1]["seeds"])):
        target, field, scope_key = key
        p = info["patch"]
        seed_count = len(info["seeds"])
        robust = "YES" if seed_count == len(SEEDS) else f"{seed_count}/{len(SEEDS)}"
        val_str = str(p.value) if len(str(p.value)) <= 8 else str(p.value)[:7] + ".."
        print(f"  {target:<25} {field:<25} {scope_key:<22} {val_str:>8} {seed_count:>6} {robust:>8}")

    # Regression report
    print("\n── Regression report ──")
    regressions_found = []
    for seed in SEEDS:
        for profile in PROFILES:
            base = baseline_results[(seed, profile)]["score"]
            patched = patched_results[(seed, profile)]["score"]
            if patched < base:
                regressions_found.append({
                    "seed": seed,
                    "profile": profile,
                    "base": base,
                    "patched": patched,
                    "delta": patched - base,
                })

    if regressions_found:
        print(f"  ⚠️  {len(regressions_found)} regression(s) detected:")
        for r in regressions_found:
            print(f"    seed={r['seed']} profile={r['profile']}: {r['base']} → {r['patched']} ({r['delta']:+d})")
    else:
        print("  ✓ No regressions detected across any seed/profile combination")

    # Stability score
    total_runs = len(SEEDS) * len(PROFILES)
    improved = sum(
        1 for seed in SEEDS for profile in PROFILES
        if patched_results[(seed, profile)]["score"] > baseline_results[(seed, profile)]["score"]
    )
    neutral = sum(
        1 for seed in SEEDS for profile in PROFILES
        if patched_results[(seed, profile)]["score"] == baseline_results[(seed, profile)]["score"]
    )
    regressed = sum(
        1 for seed in SEEDS for profile in PROFILES
        if patched_results[(seed, profile)]["score"] < baseline_results[(seed, profile)]["score"]
    )
    stability = (improved + neutral) / total_runs * 100

    print(f"\n── Stability score ──")
    print(f"  Total runs:     {total_runs}")
    print(f"  Improved:       {improved} ({improved/total_runs*100:.0f}%)")
    print(f"  Neutral:        {neutral} ({neutral/total_runs*100:.0f}%)")
    print(f"  Regressed:      {regressed} ({regressed/total_runs*100:.0f}%)")
    print(f"  Stability:      {stability:.0f}%")
    print(f"  Verdict:        {'ROBUST' if stability >= 90 and regressed == 0 else 'PARTIAL' if stability >= 70 else 'UNSTABLE'}")

    # Variance analysis
    print(f"\n── Variance analysis ──")
    print(f"  {'Profile':<22} {'Base std':>9} {'Patched std':>12} {'Spread':>8}")
    print(f"  {'-'*22} {'-'*9} {'-'*12} {'-'*8}")
    import statistics
    for profile in PROFILES:
        base_scores = [baseline_results[(s, profile)]["score"] for s in SEEDS]
        patched_scores = [patched_results[(s, profile)]["score"] for s in SEEDS]
        base_std = statistics.stdev(base_scores) if len(base_scores) > 1 else 0
        patched_std = statistics.stdev(patched_scores) if len(patched_scores) > 1 else 0
        spread = "narrower" if patched_std < base_std else "wider" if patched_std > base_std else "same"
        print(f"  {profile:<22} {base_std:>9.1f} {patched_std:>12.1f} {spread:>8}")


if __name__ == "__main__":
    main()
