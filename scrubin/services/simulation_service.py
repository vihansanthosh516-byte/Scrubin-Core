import uuid
import asyncio
import random

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ProcedureAgent
from scrubin.patient.profile import PatientProfile, PATIENT_PROFILES, STANDARD_PATIENT
from scrubin.tester.profiles.registry import PROFILES, StressProfile

from scrubin.projections.state import StateProjection
from scrubin.projections.event import EventProjection
from scrubin.projections.decision import DecisionProjection
from scrubin.api.mappers import map_option_to_dto, StateSnapshotDTO

class SimulationService:
    def __init__(self, session_id: str, seed: int, profile_name: str, patient_profile_id: str, mode: str):
        self.session_id = session_id
        self.seed = seed
        self.profile_name = profile_name
        self.patient_profile_id = patient_profile_id
        self.mode = mode
        
        self.profile = PROFILES.get(profile_name, StressProfile)()
        self.patient_profile = PATIENT_PROFILES.get(patient_profile_id, STANDARD_PATIENT)
        
        random.seed(seed)
        config = ConfigLayer(active_profile=profile_name)
        
        self.orchestrator = Orchestrator(
            seed=seed,
            config=config,
            active_profile=profile_name,
            patient_profile=self.patient_profile,
            mode=mode,
        )
        
        # Setup Projections
        self.state_proj = StateProjection(self.patient_profile_id, self.mode)
        self.event_proj = EventProjection()
        self.decision_proj = DecisionProjection()
        
        self.orchestrator.register_projection(self.state_proj)
        self.orchestrator.register_projection(self.event_proj)
        self.orchestrator.register_projection(self.decision_proj)

        # Wire Agents
        SimulationAgent().setup(self.orchestrator)
        self._wire_vitals(self.orchestrator, self.profile, self.patient_profile)
        self._wire_complication(self.orchestrator, self.profile)
        self._wire_signal_agent(self.orchestrator, self.profile)
        self._wire_decision(self.orchestrator)
        
        self.orchestrator.setup()
        self.event_queue = asyncio.Queue()

def tick_session(self, steps: int = 1):
    for _ in range(steps):
        self.orchestrator.tick()
    # Emit updated state after ticking
    self._push_snapshot_event()

    def apply_decision(self, option_id: str, target: str = "") -> dict:
        if self.mode != "interactive":
            return {"executed": False, "reason": "not interactive mode"}
        result = self.orchestrator.apply_user_decision(option_id, target)
        intent_id = ""
        if self.orchestrator.authority.execution_log:
            last = self.orchestrator.authority.execution_log[-1]
            intent_id = last.intent_id
        # Emit updated state snapshot after applying decision
        self._push_snapshot_event()
        return {
            "executed": result.get("executed", False),
            "action": result.get("action", ""),
            "target": result.get("target", ""),
            "reason": result.get("reason", ""),
            "intent_id": intent_id,
        }

    def get_snapshot(self) -> dict:
        state_snap = self.state_proj.get_snapshot()
        return state_snap

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        return self.event_proj.get_recent(limit)

    def get_events_since(self, sequence: int) -> list[dict]:
        return self.event_proj.events_after(sequence)

    def get_options(self) -> list[dict]:
        decision_snap = self.decision_proj.get_snapshot()
        options = decision_snap.get("options", [])
        return [map_option_to_dto(o).to_dict() for o in options]

    def get_summary(self) -> dict:
        state_snap = self.state_proj.get_snapshot()
        decision_snap = self.decision_proj.get_snapshot()
        
        snap = StateSnapshotDTO(
            tick=state_snap["tick"],
            vitals=state_snap["vitals"],
            active_complication=state_snap["active_complication"],
            last_procedure=state_snap["last_procedure"],
            last_decision=decision_snap["last_decision"],
            last_validation=decision_snap["last_validation"],
            last_execution=decision_snap["last_execution"],
            patient_profile=state_snap["patient_profile"],
            mode=state_snap["mode"],
            options=self.get_options(),
        )
        return snap.to_dict()

    def current_tick(self) -> int:
        return self.state_proj.current_tick

    def _push_snapshot_event(self):
        """Enqueue a state_snapshot event for WebSocket listeners."""
        try:
            snapshot = self.get_summary()
            self.event_queue.put_nowait({"type": "state_snapshot", "summary": snapshot})
        except Exception as e:
            print(f"[SimulationService] Failed to enqueue state_snapshot: {e}")

    def _wire_vitals(self, orch, profile, patient_profile):
        from scrubin.tester.runner import _ProfiledVitalsAgent
        _ProfiledVitalsAgent(profile).setup(orch)

    def _wire_complication(self, orch, profile):
        from scrubin.tester.runner import _ProfiledComplicationAgent
        _ProfiledComplicationAgent(profile).setup(orch)

    def _wire_signal_agent(self, orch, profile):
        if profile.procedure_enabled:
            ProcedureAgent().setup(orch)
        else:
            from scrubin.tester.runner import _NoOpProcedureAgent
            _NoOpProcedureAgent().setup(orch)

    def _wire_decision(self, orch):
        from scrubin.decision.engine import DecisionEngine
        from scrubin.decision.validator import DecisionValidator
        recovery_window = orch.config.get("procedures.yaml", "recovery_window", 5)
        orch.decision_engine = DecisionEngine(recovery_window=recovery_window)
        orch.decision_validator = DecisionValidator(
            horizons=[1, 3, 5],
            weights={1: 0.2, 3: 0.4, 5: 0.4},
            recovery_window=recovery_window,
        )

    @classmethod
    def create_session(cls, seed: int, profile_name: str, patient_profile_id: str = "standard", mode: str = "autonomous"):
        session_id = uuid.uuid4().hex[:12]
        return cls(session_id, seed, profile_name, patient_profile_id, mode)

    def reset_session(self):
        # Create a new service instance to replace this one in the manager
        new_svc = SimulationService(
            session_id=self.session_id,
            seed=self.seed,
            profile_name=self.profile_name,
            patient_profile_id=self.patient_profile_id,
            mode=self.mode,
        )
        return new_svc
