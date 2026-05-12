import random

from scrubin.complications.registry import ComplicationRegistry
from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ProcedureAgent
from .checks.structure import StructureCheck
from .checks.physiology import PhysiologyCheck
from .checks.causality import CausalityCheck
from .checks.recovery import RecoveryCheck
from .scoring import ScoreEngine
from .models import TestRun, TestFinding
from .profiles.registry import StressProfile, PROFILES


class _ProfiledVitalsAgent(VitalsAgent):
    def __init__(self, profile: StressProfile):
        super().__init__()
        self._profile = profile

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        config = getattr(orchestrator, 'config', None) or ConfigLayer()
        base_ranges = config.get_vital_ranges()
        ranges = {**base_ranges, **self._profile.vitals_override}
        self.VITAL_RANGES = ranges
        self._state = {k: sum(v) / 2 for k, v in ranges.items()}
        self._ranges = ranges
        self._drift = self._profile.vitals_drift
        self._pending_effects: list[dict] = []
        orchestrator.register_agent("system.boot", self._on_boot)
        orchestrator.register_agent("tick", self._on_tick)
        orchestrator.register_agent("procedure", self._on_procedure)

    def _on_boot(self, event) -> None:
        print(f"[VitalsAgent] boot vitals={self._state}")

    def _on_tick(self, event) -> None:
        tick = event.payload.get("tick", 0)
        vitals = {}
        for key, (lo, hi) in self._ranges.items():
            current = self._state.get(key, (lo + hi) / 2)
            delta = random.uniform(-self._drift, self._drift)
            vitals[key] = current + delta
        vitals = self._apply_pending(tick, vitals)
        vitals = self._clamp_vitals(vitals)
        self._state = vitals
        self._orchestrator.submit_vitals(tick, vitals)
        print(f"[VitalsAgent] tick={tick} vitals={vitals}")


class _ProfiledComplicationAgent(ComplicationAgent):
    def __init__(self, profile: StressProfile):
        super().__init__()
        self._profile = profile

    def setup(self, orchestrator) -> None:
        self._orchestrator = orchestrator
        self._lifecycles = {}
        self._prob = self._profile.complication_prob
        self._complication_ids = (
            self._profile.complication_list
            if self._profile.complication_list
            else ComplicationRegistry.get_ids()
        )
        orchestrator.register_agent("tick", self._on_tick)

    def _on_tick(self, event) -> None:
        tick = event.payload.get("tick", 0)
        from scrubin.clinical.lifecycle import ComplicationLifecycle, ComplicationStatus
        
        # Evaluate existing lifecycles
        for comp_id, lifecycle in self._lifecycles.items():
            # For simplicity in testing profile, skip vitals/interventions
            transition_event = lifecycle.evaluate(tick, {}, [])
            if transition_event:
                self._orchestrator.bus.publish(
                    "complication_transition",
                    {
                        "tick": tick,
                        "complication": comp_id,
                        "from_status": transition_event.from_status.value,
                        "to_status": transition_event.to_status.value,
                        "reason": transition_event.reason
                    }
                )
                if transition_event.to_status == ComplicationStatus.ESCALATING:
                    self._orchestrator.bus.publish(
                        "complication_escalation",
                        {"tick": tick, "complication": comp_id, "severity": "severe", "onset_tick": lifecycle.start_tick},
                    )

        if random.random() < self._prob and not self._lifecycles:
            complication = random.choice(self._complication_ids)
            severity = self._determine_initial_severity(complication)
            lifecycle = ComplicationLifecycle(complication, tick, severity)
            self._lifecycles[complication] = lifecycle
            self._orchestrator.bus.publish(
                "complication",
                {"tick": tick, "complication": complication, "severity": severity},
            )
            print(f"[ComplicationAgent] tick={tick} complication={complication} severity={severity}")
        else:
            print(f"[ComplicationAgent] tick={tick} no complication")

    @property
    def complications(self):
        from scrubin.clinical.lifecycle import ComplicationStatus
        from scrubin.models.types import ComplicationState
        return [
            ComplicationState(id=lc.name, severity=lc.severity, onset_tick=lc.start_tick)
            for lc in self._lifecycles.values() if lc.status not in (ComplicationStatus.RESOLVED, ComplicationStatus.LATENT)
        ]


class _NoOpProcedureAgent:
    def setup(self, orchestrator) -> None:
        orchestrator.register_agent("complication", self._on_complication)

    def _on_complication(self, event) -> None:
        tick = event.payload.get("tick", 0)
        complication = event.payload.get("complication")
        print(f"[ComplicationSignalAgent] tick={tick} SUPPRESSED for={complication}")


class TestRunner:
    def __init__(self, seed: int = 0, ticks: int = 10, profile: str = "default",
                 registry_path: str = None, logic_patches: list = None):
        self.seed = seed
        self.ticks = ticks
        self.profile_name = profile
        self.profile = PROFILES.get(profile, StressProfile)()
        self._registry_path = registry_path
        self._logic_patches = logic_patches or []

    def _wire_decision_pipeline(self, orch, proc_enabled):
        from scrubin.decision.engine import DecisionEngine
        from scrubin.decision.validator import DecisionValidator
        recovery_window = orch.config.get("procedures.yaml", "recovery_window", 5)
        engine = DecisionEngine(recovery_window=recovery_window)
        validator = DecisionValidator(
            horizons=[1, 3, 5],
            weights={1: 0.2, 3: 0.4, 5: 0.4},
            recovery_window=recovery_window,
        )
        orch.decision_engine = engine
        orch.decision_validator = validator
        if not proc_enabled:
            print("[TestRunner] decision pipeline active (procedure_enabled=False → authority-only path)")

    def run(self) -> TestRun:
        random.seed(self.seed)

        config = ConfigLayer(
            registry_path=self._registry_path,
            active_profile=self.profile_name,
        )
        orch = Orchestrator(seed=self.seed, config=config, active_profile=self.profile_name)
        SimulationAgent().setup(orch)
        _ProfiledVitalsAgent(self.profile).setup(orch)
        _ProfiledComplicationAgent(self.profile).setup(orch)

        proc_enabled = self.profile.procedure_enabled
        if "agents/procedure.py" in config._overrides and "procedure_enabled" in config._overrides["agents/procedure.py"]:
            proc_enabled = config._overrides["agents/procedure.py"]["procedure_enabled"]

        all_logic = list(self._logic_patches)
        if config.logic_entries:
            from scrubin.improvement.patches import Patch
            for le in config.logic_entries:
                all_logic.append(Patch(
                    target=le["target"],
                    action=le.get("action", ""),
                    path=le.get("path", ""),
                    value=le.get("new_value", True),
                    reason=le.get("reason", ""),
                    scope=le.get("scope", {"profile": self.profile_name}),
                    priority=le.get("priority", 0),
                    patch_type="logic",
                    target_path=le.get("target_path", ""),
                ))
            if le["target"] == "agents/procedure.py" and le.get("path") == "procedure_enabled":
                if le.get("new_value") is True:
                    proc_enabled = True

        if proc_enabled:
            signal_agent = ProcedureAgent()
            logic_for_procedure = [
                p for p in all_logic
                if p.patch_type == "logic" and p.target == "agents/procedure.py"
            ]
            if logic_for_procedure:
                from scrubin.improvement.logic_executor import apply_logic_patches
                signal_agent = apply_logic_patches(signal_agent, logic_for_procedure)
            signal_agent.setup(orch)
        else:
            _NoOpProcedureAgent().setup(orch)
        self._wire_decision_pipeline(orch, proc_enabled)

        orch.setup()

        for _ in range(self.ticks):
            orch.tick()

        exec_events = [e for e in orch.ledger.all() if e.type == "decision_execution" and e.payload.get("executed")]
        if exec_events:
            print(f"[TestRunner] authority executed {len(exec_events)} procedure event(s)")

        ledger = orch.ledger.all()

        findings: list[TestFinding] = []
        findings += StructureCheck().run(ledger)
        findings += PhysiologyCheck(profile=self.profile).run(ledger)
        findings += CausalityCheck(config=config).run(ledger)
        findings += RecoveryCheck(config=config).run(ledger)

        score = ScoreEngine().compute(ledger, findings)

        return TestRun(
            seed=self.seed,
            ticks=self.ticks,
            ledger_size=len(ledger),
            findings=findings,
            score=score,
            metadata={"profile": self.profile_name},
        )
