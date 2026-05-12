import json
import os
import sys
import random
import statistics

from scrubin.tester.runner import TestRunner
from scrubin.improvement.engine import ImprovementEngine
from scrubin.improvement.optimizer import (
    IterativeImprover, PatchImpactMeasurer, PatchSelector,
    PatchInteractionTester, PatchAttributionLog, OptimizationResult,
)
from scrubin.improvement.registry import PatchRegistry


SEEDS = [1, 7, 42, 99, 123]
PROFILES = ["default", "hypoxia", "broken_procedure", "recovery_suppression", "causality_race"]
TICKS = 10
REGISTRY_PATH = os.path.abspath("patch_registry.json")


def run_baseline(seed, profile):
    runner = TestRunner(seed=seed, ticks=TICKS, profile=profile)
    return runner.run()


def main():
    print("=" * 75)
    print("  SCRUBIN PATCH OPTIMIZATION LOOP EVALUATION")
    print("=" * 75)

    # ── Phase 1: Baseline ──────────────────────────────────────
    print("\n── PHASE 1: Baseline (no patches) ──")
    baseline_scores = {}
    for seed in SEEDS:
        for profile in PROFILES:
            result = run_baseline(seed, profile)
            baseline_scores[(seed, profile)] = result.score
            status = "✓" if result.score >= 80 else "✗" if result.score < 50 else "△"
            print(f"  seed={seed:>3} profile={profile:<22} score={result.score:>3}/100 {status}")

    # ── Phase 2: Run optimization loop per seed/profile ────────
    print("\n── PHASE 2: Iterative optimization per seed/profile ──")
    os.makedirs("/tmp/opencode", exist_ok=True)

    opt_results: list[OptimizationResult] = {}
    for profile in PROFILES:
        for seed in SEEDS:
            key = (seed, profile)
            if baseline_scores[key] >= 100:
                opt_results[key] = OptimizationResult(
                    profile=profile, seed=seed,
                    baseline_score=100, final_score=100, total_delta=0,
                    iterations=0, accepted_patches=[], rejected_patches=[],
                    cancelled_pairs=[], impact_log=[],
                )
                print(f"  seed={seed:>3} profile={profile:<22} SKIP (already 100)")
                continue

            tmp_registry = f"/tmp/opencode/registry_{seed}_{profile}.json"
            if os.path.exists(tmp_registry):
                os.remove(tmp_registry)

            improver = IterativeImprover(max_iterations=5, top_k=3)
            result = improver.optimize(
                seed=seed, ticks=TICKS, profile=profile,
                registry_path=tmp_registry,
            )
            opt_results[key] = result

            delta = result.total_delta
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            accepted = len(result.accepted_patches)
            iters = result.iterations
            print(f"  seed={seed:>3} profile={profile:<22} "
                  f"{result.baseline_score}→{result.final_score} {arrow}{delta:+d} "
                  f"iters={iters} accepted={accepted}")

    # ── Phase 3: Merge best patches into final registry ────────
    print("\n── PHASE 3: Merge accepted patches into final registry ──")
    if os.path.exists(REGISTRY_PATH):
        os.remove(REGISTRY_PATH)
    final_registry = PatchRegistry()

    all_accepted = {}
    for key, result in opt_results.items():
        for p in result.accepted_patches:
            scope_key = p.scope.get("profile", "default")
            dedup = (p.target, p.path, str(p.value), scope_key)
            if dedup not in all_accepted:
                all_accepted[dedup] = {"patch": p, "count": 1, "total_delta": result.total_delta}
            else:
                all_accepted[dedup]["count"] += 1
                all_accepted[dedup]["total_delta"] += result.total_delta

    for dedup, info in sorted(all_accepted.items(), key=lambda x: -x[1]["count"]):
        p = info["patch"]
        final_registry.record(
            target=p.target, field=p.path, new_value=p.value,
            reason=p.reason, scope=p.scope, priority=p.priority,
        )

    print(f"  Final registry: {len(final_registry.entries)} entries")

    # ── Phase 4: Validate with final registry ──────────────────
    print("\n── PHASE 4: Validation with optimized registry ──")
    optimized_scores = {}
    for seed in SEEDS:
        for profile in PROFILES:
            key = (seed, profile)
            result = run_baseline(seed, profile)
            optimized_scores[key] = result.score
            base = baseline_scores[key]
            delta = result.score - base
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            print(f"  seed={seed:>3} profile={profile:<22} "
                  f"score={result.score:>3}/100 (base={base} {arrow}{delta:+d})")

    # ── Phase 5: Analysis ──────────────────────────────────────
    print("\n" + "=" * 75)
    print("  OPTIMIZATION ANALYSIS")
    print("=" * 75)

    # Per-profile comparison
    print("\n── Score comparison by profile ──")
    print(f"  {'Profile':<22} {'Base avg':>8} {'Opt avg':>8} {'Delta':>7} {'Improve':>8} {'Regress':>8}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*8}")

    for profile in PROFILES:
        base = [baseline_scores[(s, profile)] for s in SEEDS]
        opt = [optimized_scores[(s, profile)] for s in SEEDS]
        deltas = [o - b for b, o in zip(base, opt)]
        avg_base = sum(base) / len(base)
        avg_opt = sum(opt) / len(opt)
        avg_delta = avg_opt - avg_base
        improved = sum(1 for d in deltas if d > 0)
        regressed = sum(1 for d in deltas if d < 0)
        print(f"  {profile:<22} {avg_base:>8.1f} {avg_opt:>8.1f} {avg_delta:>+7.1f} "
              f"{improved:>5}/{len(SEEDS)} {regressed:>5}/{len(SEEDS)}")

    # Per-seed comparison
    print("\n── Score comparison by seed ──")
    print(f"  {'Seed':>5} {'Base avg':>8} {'Opt avg':>8} {'Delta':>7}")
    print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*7}")

    for seed in SEEDS:
        base = [baseline_scores[(seed, p)] for p in PROFILES]
        opt = [optimized_scores[(seed, p)] for p in PROFILES]
        avg_base = sum(base) / len(base)
        avg_opt = sum(opt) / len(opt)
        avg_delta = avg_opt - avg_base
        print(f"  {seed:>5} {avg_base:>8.1f} {avg_opt:>8.1f} {avg_delta:>+7.1f}")

    # Patch effectiveness ranking
    print("\n── Patch effectiveness ranking ──")
    print(f"  {'Target':<25} {'Field':<25} {'Scope':<22} {'Count':>6} {'Avg delta':>10}")
    print(f"  {'-'*25} {'-'*25} {'-'*22} {'-'*6} {'-'*10}")

    for dedup, info in sorted(all_accepted.items(), key=lambda x: -x[1]["count"]):
        target, path, value, scope_key = dedup
        count = info["count"]
        avg_delta = info["total_delta"] / max(count, 1)
        val_str = value if len(str(value)) <= 10 else str(value)[:9] + ".."
        print(f"  {target:<25} {path:<25} {scope_key:<22} {count:>6} {avg_delta:>+10.1f}")

    # Interaction analysis
    print("\n── Patch interaction analysis ──")
    all_cancelled = []
    for key, result in opt_results.items():
        for pair in result.cancelled_pairs:
            all_cancelled.append((key, pair))

    if all_cancelled:
        print(f"  ⚠️  {len(all_cancelled)} cancellation(s) detected:")
        for (seed, profile), (patches, expected, actual) in all_cancelled:
            print(f"    seed={seed} profile={profile}: {patches} "
                  f"expected={expected} actual={actual}")
    else:
        print("  ✓ No patch cancellations detected")

    # Impact log summary
    print("\n── Per-patch impact summary ──")
    impact_by_patch = {}
    for key, result in opt_results.items():
        for entry in result.impact_log:
            pk = (entry["patch"], entry["scope"].get("profile", "default"))
            if pk not in impact_by_patch:
                impact_by_patch[pk] = {"deltas": [], "improves": 0, "total": 0}
            impact_by_patch[pk]["deltas"].append(entry["solo_delta"])
            impact_by_patch[pk]["total"] += 1
            if entry["improves"]:
                impact_by_patch[pk]["improves"] += 1

    print(f"  {'Patch':<40} {'Scope':<22} {'AvgΔ':>6} {'Best':>5} {'Hit':>5}")
    print(f"  {'-'*40} {'-'*22} {'-'*6} {'-'*5} {'-'*5}")
    for pk, info in sorted(impact_by_patch.items(), key=lambda x: -sum(x[1]["deltas"])):
        patch_str, scope_str = pk
        avg_d = sum(info["deltas"]) / max(len(info["deltas"]), 1)
        best = max(info["deltas"]) if info["deltas"] else 0
        hit = f"{info['improves']}/{info['total']}"
        print(f"  {patch_str:<40} {scope_str:<22} {avg_d:>+6.1f} {best:>+5} {hit:>5}")

    # Optimization loop statistics
    print("\n── Optimization loop statistics ──")
    total_runs = len(SEEDS) * len(PROFILES)
    improved = sum(1 for key in opt_results if opt_results[key].total_delta > 0)
    neutral = sum(1 for key in opt_results if opt_results[key].total_delta == 0)
    regressed = sum(1 for key in opt_results if opt_results[key].total_delta < 0)
    total_patches = sum(len(r.accepted_patches) for r in opt_results.values())
    total_iters = sum(r.iterations for r in opt_results.values())
    total_duration = sum(r.duration_ms for r in opt_results.values())

    print(f"  Total seed/profile combos:  {total_runs}")
    print(f"  Improved:                   {improved} ({improved/total_runs*100:.0f}%)")
    print(f"  Neutral:                    {neutral} ({neutral/total_runs*100:.0f}%)")
    print(f"  Regressed:                  {regressed} ({regressed/total_runs*100:.0f}%)")
    print(f"  Total patches accepted:     {total_patches}")
    print(f"  Total iterations:           {total_iters}")
    print(f"  Total optimization time:    {total_duration:.0f}ms")
    print(f"  Avg iterations per combo:   {total_iters/max(total_runs,1):.1f}")

    # Overall improvement
    base_sum = sum(baseline_scores.values())
    opt_sum = sum(optimized_scores.values())
    print(f"\n  Baseline total:             {base_sum}/{total_runs*100}")
    print(f"  Optimized total:            {opt_sum}/{total_runs*100}")
    print(f"  Overall improvement:        {opt_sum - base_sum:+d} points")


if __name__ == "__main__":
    main()
