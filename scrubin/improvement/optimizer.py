import json
import os
import time
import random
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from scrubin.tester.runner import TestRunner
from scrubin.improvement.engine import ImprovementEngine
from scrubin.improvement.patches import Patch
from scrubin.improvement.registry import PatchRegistry
from scrubin.core.config import ConfigLayer


@dataclass
class PatchImpact:
    patch: Patch
    solo_delta: int = 0
    combo_delta: int = 0
    baseline_score: int = 0
    patched_score: int = 0
    findings_before: int = 0
    findings_after: int = 0
    improves: bool = False
    cancels_with: list = field(default_factory=list)


@dataclass
class OptimizationResult:
    profile: str
    seed: int
    baseline_score: int
    final_score: int
    total_delta: int
    iterations: int
    accepted_patches: list
    rejected_patches: list
    cancelled_pairs: list
    impact_log: list
    duration_ms: float = 0.0


class PatchAttributionLog:
    def __init__(self, path: str = None):
        self._path = path or os.path.join(
            os.path.dirname(__file__), "..", "..", "patch_attribution.json"
        )
        self._path = os.path.abspath(self._path)
        self._records: list[dict] = []

    def record(self, profile: str, seed: int, patch_key: str,
               score_before: int, score_after: int, context: str = "solo"):
        self._records.append({
            "profile": profile,
            "seed": seed,
            "patch": patch_key,
            "score_before": score_before,
            "score_after": score_after,
            "delta": score_after - score_before,
            "context": context,
            "timestamp": time.time(),
        })

    def save(self):
        with open(self._path, "w") as f:
            json.dump(self._records, f, indent=2)

    @property
    def records(self) -> list[dict]:
        return list(self._records)

    def clear(self):
        self._records = []


def _record_patch(registry, patch):
    registry.record(
        target=patch.target, field=patch.path, new_value=patch.value,
        reason=patch.reason, scope=patch.scope, priority=patch.priority,
        patch_type=patch.patch_type, target_path=patch.target_path,
        action=patch.action,
    )


class PatchImpactMeasurer:
    def __init__(self, seed: int, ticks: int, profile: str,
                 registry_path: str = None, attribution: PatchAttributionLog = None):
        self._seed = seed
        self._ticks = ticks
        self._profile = profile
        self._registry_path = registry_path
        self._attribution = attribution or PatchAttributionLog()

    def _run_with_patch(self, patch: Patch):
        logic_patches = [patch] if patch.patch_type == "logic" else []
        config_patches = [] if patch.patch_type == "logic" else [patch]
        tmp_path = self._registry_path + ".tmp_measure"
        registry = PatchRegistry(path=tmp_path)
        registry.clear()
        for cp in config_patches:
            _record_patch(registry, cp)
        random.seed(self._seed)
        runner = TestRunner(
            seed=self._seed, ticks=self._ticks, profile=self._profile,
            registry_path=tmp_path, logic_patches=logic_patches,
        )
        result = runner.run()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return result.score, len(result.findings)

    def _run_baseline(self):
        tmp_path = self._registry_path + ".tmp_measure"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        registry = PatchRegistry(path=tmp_path)
        registry.clear()
        random.seed(self._seed)
        runner = TestRunner(
            seed=self._seed, ticks=self._ticks, profile=self._profile,
            registry_path=tmp_path, logic_patches=[],
        )
        result = runner.run()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return result.score, len(result.findings)

    def measure_solo(self, patches: list):
        baseline_score, baseline_findings = self._run_baseline()
        impacts = []
        for patch in patches:
            patched_score, patched_findings = self._run_with_patch(patch)
            delta = patched_score - baseline_score
            key = f"{patch.patch_type}:{patch.target}:{patch.path}={patch.value}"
            self._attribution.record(
                profile=self._profile, seed=self._seed,
                patch_key=key, score_before=baseline_score,
                score_after=patched_score, context="solo",
            )
            impacts.append(PatchImpact(
                patch=patch, solo_delta=delta,
                baseline_score=baseline_score, patched_score=patched_score,
                findings_before=baseline_findings, findings_after=patched_findings,
                improves=delta > 0,
            ))
        return impacts, baseline_score


class PatchInteractionTester:
    def __init__(self, seed: int, ticks: int, profile: str,
                 registry_path: str = None, attribution: PatchAttributionLog = None):
        self._seed = seed
        self._ticks = ticks
        self._profile = profile
        self._registry_path = registry_path
        self._attribution = attribution or PatchAttributionLog()

    def test_combinations(self, impacts, baseline_score, max_k=3):
        improving = [i for i in impacts if i.improves]
        if len(improving) <= 1:
            return impacts, []
        cancelled_pairs = []
        for k in range(2, min(max_k + 1, len(improving) + 1)):
            for combo in combinations(improving, k):
                patches = [i.patch for i in combo]
                expected = sum(i.solo_delta for i in combo)
                actual = self._run_with_patches(patches)
                combo_key = " + ".join(
                    f"{i.patch.target}:{i.patch.path}" for i in combo
                )
                self._attribution.record(
                    profile=self._profile, seed=self._seed,
                    patch_key=combo_key, score_before=baseline_score,
                    score_after=actual, context=f"combo_k{k}",
                )
                for i in combo:
                    i.combo_delta = actual - baseline_score
                if actual < baseline_score:
                    cancelled_pairs.append((
                        [f"{i.patch.target}:{i.patch.path}" for i in combo],
                        expected, actual,
                    ))
        return impacts, cancelled_pairs

    def _run_with_patches(self, patches: list):
        logic_patches = [p for p in patches if p.patch_type == "logic"]
        config_patches = [p for p in patches if p.patch_type != "logic"]
        tmp_path = (self._registry_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "patch_registry.json")
        )) + ".tmp_interact"
        registry = PatchRegistry(path=tmp_path)
        registry.clear()
        for p in config_patches:
            _record_patch(registry, p)
        random.seed(self._seed)
        runner = TestRunner(
            seed=self._seed, ticks=self._ticks, profile=self._profile,
            registry_path=tmp_path, logic_patches=logic_patches,
        )
        result = runner.run()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return result.score


class PatchSelector:
    def __init__(self, top_k: int = 3):
        self._top_k = top_k

    def select(self, impacts: list):
        ranked = sorted(impacts, key=lambda i: i.solo_delta, reverse=True)
        improving = [i for i in ranked if i.improves]
        return [i.patch for i in improving[:self._top_k]]


class IterativeImprover:
    def __init__(self, max_iterations: int = 5, top_k: int = 3):
        self._max_iterations = max_iterations
        self._top_k = top_k

    def optimize(self, seed: int, ticks: int, profile: str,
                 registry_path: str = None) -> OptimizationResult:
        start = time.time()
        registry_path = registry_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "patch_registry.json")
        )
        attribution = PatchAttributionLog()
        baseline_runner = TestRunner(
            seed=seed, ticks=ticks, profile=profile, registry_path=registry_path,
        )
        random.seed(seed)
        baseline_run = baseline_runner.run()
        baseline_score = baseline_run.score
        # -- state --
        accepted_patches = []
        accepted_logic_patches = []
        rejected_patches = []
        cancelled_pairs = []
        impact_log = []
        current_score = baseline_score
        best_registry = PatchRegistry(path=registry_path)
        best_registry.clear()
        last_iteration = 0
        had_candidates = False
        # -- loop --
        for iteration in range(1, self._max_iterations + 1):
            last_iteration = iteration
            tmp_path = registry_path + f".tmp_iter_{iteration}"
            working_registry = PatchRegistry(path=tmp_path)
            working_registry.clear()
            accepted_config = [p for p in accepted_patches if p.patch_type != "logic"]
            for p in accepted_config:
                _record_patch(working_registry, p)
            # run with current accepted patches
            random.seed(seed)
            runner = TestRunner(
                seed=seed, ticks=ticks, profile=profile,
                registry_path=tmp_path, logic_patches=accepted_logic_patches,
            )
            current_run = runner.run()
            # generate new candidates
            engine = ImprovementEngine()
            analysis = engine.analyze(current_run, profile=profile)
            candidate_patches = analysis["patches"]
            had_candidates = bool(candidate_patches)
            if not candidate_patches:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                break
            # dedup candidates
            seen = set()
            unique_candidates = []
            for p in candidate_patches:
                pk = (p.target, p.path, str(p.value), p.scope.get("profile", "default"), p.patch_type)
                if pk not in seen:
                    seen.add(pk)
                    unique_candidates.append(p)
            # filter already-applied
            already_applied = {
                (p.target, p.path, p.patch_type, p.scope.get("profile", "default"))
                for p in accepted_patches
            }
            novel_candidates = [
                p for p in unique_candidates
                if (p.target, p.path, p.patch_type, p.scope.get("profile", "default")) not in already_applied
            ]
            if not novel_candidates:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                break
            # measure each patch solo
            measurer = PatchImpactMeasurer(
                seed=seed, ticks=ticks, profile=profile,
                registry_path=registry_path, attribution=attribution,
            )
            impacts, measure_baseline = measurer.measure_solo(novel_candidates)
            for imp in impacts:
                impact_log.append({
                    "iteration": iteration,
                    "patch": f"{imp.patch.patch_type}:{imp.patch.target}:{imp.patch.path}={imp.patch.value}",
                    "scope": imp.patch.scope,
                    "solo_delta": imp.solo_delta,
                    "improves": imp.improves,
                    "patch_type": imp.patch.patch_type,
                })
            # select top-k
            selector = PatchSelector(top_k=self._top_k)
            selected = selector.select(impacts)
            if not selected:
                for imp in impacts:
                    if not imp.improves:
                        rejected_patches.append(imp.patch)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                break
            # test interactions if multiple
            if len(selected) > 1:
                interaction_tester = PatchInteractionTester(
                    seed=seed, ticks=ticks, profile=profile,
                    registry_path=registry_path, attribution=attribution,
                )
                improving_impacts = [i for i in impacts if i.improves]
                impacts, cancelled = interaction_tester.test_combinations(
                    improving_impacts, measure_baseline,
                )
                cancelled_pairs.extend(cancelled)
            # accept patches
            for patch in selected:
                accepted_patches.append(patch)
                if patch.patch_type == "logic":
                    accepted_logic_patches.append(patch)
                key = f"{patch.patch_type}:{patch.target}:{patch.path}={patch.value}"
                attribution.record(
                    profile=profile, seed=seed,
                    patch_key=key, score_before=measure_baseline,
                    score_after=measure_baseline + sum(
                        i.solo_delta for i in impacts
                        if i.patch is patch and i.improves
                    ),
                    context=f"iter_{iteration}_accepted",
                )
            # verify combined effect
            verify_registry = PatchRegistry(path=tmp_path)
            verify_registry.clear()
            verify_config = [p for p in accepted_patches if p.patch_type != "logic"]
            for p in verify_config:
                _record_patch(verify_registry, p)
            random.seed(seed)
            verify_runner = TestRunner(
                seed=seed, ticks=ticks, profile=profile,
                registry_path=tmp_path, logic_patches=accepted_logic_patches,
            )
            verify_run = verify_runner.run()
            current_score = verify_run.score
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if current_score >= 100:
                break
        # -- finalize --
        best_registry.clear()
        for p in accepted_patches:
            _record_patch(best_registry, p)
        attribution.save()
        duration = (time.time() - start) * 1000
        return OptimizationResult(
            profile=profile,
            seed=seed,
            baseline_score=baseline_score,
            final_score=current_score,
            total_delta=current_score - baseline_score,
            iterations=last_iteration if had_candidates else 0,
            accepted_patches=accepted_patches,
            rejected_patches=rejected_patches,
            cancelled_pairs=cancelled_pairs,
            impact_log=impact_log,
            duration_ms=duration,
        )
