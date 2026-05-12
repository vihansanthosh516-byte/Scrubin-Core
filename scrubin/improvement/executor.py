import random

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ProcedureAgent
from scrubin.improvement.patches import Patch
from scrubin.improvement.registry import PatchRegistry
from scrubin.tester.runner import TestRunner
from scrubin.tester.models import TestRun
from scrubin.improvement.engine import ImprovementEngine


VITAL_RANGE_PATCH_MAP = {
    "oxygenation.min_spo2": ("spo2", 0),
    "heart_rate.max": ("heart_rate", 1),
    "heart_rate.min": ("heart_rate", 0),
    "bp_systolic.max": ("bp_systolic", 1),
    "bp_systolic.min": ("bp_systolic", 0),
}


class PatchExecutor:
    def apply_and_rerun(self, test_run: TestRun, patches: list, profile: str = "default") -> dict:
        vital_patches = [p for p in patches if p.target == "agents/vitals.py" and p.path in VITAL_RANGE_PATCH_MAP]
        original_runner = TestRunner(seed=test_run.seed, ticks=test_run.ticks, profile=profile)
        patched_runner = self._build_patched_runner(test_run, vital_patches, profile)

        _random_state = random.getstate()
        random.seed(test_run.seed)
        before_run = original_runner.run()

        random.setstate(_random_state)
        random.seed(test_run.seed)
        after_run = patched_runner.run()

        engine = ImprovementEngine()
        after_analysis = engine.analyze(after_run, profile=profile)

        registry = PatchRegistry()
        registry.record_patches(patches)

        return {
            "before_score": before_run.score,
            "after_score": after_run.score,
            "delta": after_run.score - before_run.score,
            "applied_patches": len(vital_patches),
            "remaining_findings": len(after_run.findings),
            "remaining_patches": len(after_analysis["patches"]),
            "registry_entries": len(registry.entries),
        }

    def _build_patched_runner(self, test_run, vital_patches, profile):
        config = ConfigLayer(active_profile=profile)
        patched_ranges = config.get_vital_ranges()

        for patch in vital_patches:
            key, idx = VITAL_RANGE_PATCH_MAP[patch.path]
            lo, hi = patched_ranges.get(key, (0, 100))
            if idx == 0:
                lo = patch.value
            else:
                hi = patch.value
            patched_ranges[key] = (lo, hi)

        class _PatchedVitalsAgent(VitalsAgent):
            VITAL_RANGES = patched_ranges

        class _PatchedRunner(TestRunner):
            def run(self) -> TestRun:
                random.seed(self.seed)
                config = ConfigLayer(active_profile=self.profile_name)
                orch = Orchestrator(seed=self.seed, config=config, active_profile=self.profile_name)
                SimulationAgent().setup(orch)
                _PatchedVitalsAgent().setup(orch)
                ComplicationAgent().setup(orch)
                ProcedureAgent().setup(orch)
                from scrubin.decision.engine import DecisionEngine
                from scrubin.decision.validator import DecisionValidator
                recovery_window = config.get("procedures.yaml", "recovery_window", 5)
                orch.decision_engine = DecisionEngine(recovery_window=recovery_window)
                orch.decision_validator = DecisionValidator(
                    horizons=[1, 3, 5],
                    weights={1: 0.2, 3: 0.4, 5: 0.4},
                    recovery_window=recovery_window,
                )
                orch.setup()

                for _ in range(self.ticks):
                    orch.tick()

                ledger = orch.ledger.all()
                from scrubin.tester.checks.structure import StructureCheck
                from scrubin.tester.checks.physiology import PhysiologyCheck
                from scrubin.tester.checks.causality import CausalityCheck
                from scrubin.tester.checks.recovery import RecoveryCheck
                from scrubin.tester.scoring import ScoreEngine
                from scrubin.tester.models import TestFinding

                findings: list[TestFinding] = []
                findings += StructureCheck().run(ledger)
                findings += PhysiologyCheck().run(ledger)
                findings += CausalityCheck().run(ledger)
                findings += RecoveryCheck().run(ledger)
                score = ScoreEngine().compute(findings)

                return TestRun(
                    seed=self.seed,
                    ticks=self.ticks,
                    ledger_size=len(ledger),
                    findings=findings,
                    score=score,
                    metadata={"profile": self.profile_name, "patched": True},
                )

        return _PatchedRunner(seed=test_run.seed, ticks=test_run.ticks, profile=profile)
