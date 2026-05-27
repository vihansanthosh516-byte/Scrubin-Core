from dataclasses import dataclass, field
from typing import Dict, List, Any

from scrubin.clinical.cognition.diagnostics import HiddenCondition, ClinicalFinding
from scrubin.physiology.organs.cardiovascular import OrganState
from scrubin.clinical.resources import ResourceManager

@dataclass
class PhysiologyState:
    vitals: Dict[str, float] = field(default_factory=dict)
    active_trajectories: List[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "vitals": {k: round(v, 6) for k, v in sorted(self.vitals.items())},
            "active_trajectories": [
                t.to_dict() if hasattr(t, "to_dict") else repr(t)
                for t in self.active_trajectories
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PhysiologyState":
        return cls(
            vitals=d.get("vitals", {}),
            active_trajectories=d.get("active_trajectories", []),
        )

@dataclass
class OrganSystemState:
    cardiovascular: OrganState = field(default_factory=OrganState)
    respiratory: OrganState = field(default_factory=OrganState)
    renal: OrganState = field(default_factory=OrganState)
    neurologic: OrganState = field(default_factory=OrganState)
    hematologic: OrganState = field(default_factory=OrganState)

    def to_dict(self) -> dict:
        return {
            "cardiovascular": self.cardiovascular.to_dict(),
            "respiratory": self.respiratory.to_dict(),
            "renal": self.renal.to_dict(),
            "neurologic": self.neurologic.to_dict(),
            "hematologic": self.hematologic.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OrganSystemState":
        return cls(
            cardiovascular=OrganState.from_dict(d.get("cardiovascular", {})),
            respiratory=OrganState.from_dict(d.get("respiratory", {})),
            renal=OrganState.from_dict(d.get("renal", {})),
            neurologic=OrganState.from_dict(d.get("neurologic", {})),
            hematologic=OrganState.from_dict(d.get("hematologic", {})),
        )

@dataclass
class DiagnosticBeliefState:
    hypotheses: List[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hypotheses": [
                h.to_dict() if hasattr(h, "to_dict") else repr(h)
                for h in self.hypotheses
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DiagnosticBeliefState":
        return cls(hypotheses=d.get("hypotheses", []))

@dataclass
class ForecastState:
    projected_mortality: float = 0.0
    risk_forecast: Any = None
    trajectories: List[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "projected_mortality": round(self.projected_mortality, 6),
            "risk_forecast": self.risk_forecast.to_dict() if hasattr(self.risk_forecast, "to_dict") else repr(self.risk_forecast) if self.risk_forecast is not None else None,
            "trajectories": [
                t.to_dict() if hasattr(t, "to_dict") else repr(t)
                for t in self.trajectories
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ForecastState":
        return cls(
            projected_mortality=d.get("projected_mortality", 0.0),
            risk_forecast=d.get("risk_forecast"),
            trajectories=d.get("trajectories", []),
        )

@dataclass
class SimulationWorld:
    tick: int = 0
    
    hidden_state: Dict[str, HiddenCondition] = field(default_factory=dict)
    observable_state: List[ClinicalFinding] = field(default_factory=list)
    
    physiology: PhysiologyState = field(default_factory=PhysiologyState)
    organ_state: OrganSystemState = field(default_factory=OrganSystemState)
    
    belief_state: DiagnosticBeliefState = field(default_factory=DiagnosticBeliefState)
    forecast_state: ForecastState = field(default_factory=ForecastState)
    
    resource_manager: ResourceManager = field(default_factory=ResourceManager)
    
    # Partial Observability
    observed_vitals: Dict[str, float] = field(default_factory=dict)
    diagnostic_queue: Any = None # DiagnosticQueue
    
    mortality_risk: float = 0.0
    instability_index: float = 0.0

    sofa_score: int = 0
    news2_score: int = 0

    _prev_mortality_risk: float = field(default=0.0, repr=False)

    def to_dict(self) -> dict:
        hidden = {}
        for k, v in sorted(self.hidden_state.items()):
            hidden[k] = v.to_dict() if hasattr(v, "to_dict") else repr(v)
        observable = []
        for f in self.observable_state:
            observable.append(f.to_dict() if hasattr(f, "to_dict") else repr(f))
        return {
            "tick": self.tick,
            "hidden_state": hidden,
            "observable_state": observable,
            "physiology": self.physiology.to_dict(),
            "organ_state": self.organ_state.to_dict(),
            "belief_state": self.belief_state.to_dict(),
            "forecast_state": self.forecast_state.to_dict(),
            "resource_manager": self.resource_manager.to_dict(),
            "observed_vitals": {k: round(v, 6) for k, v in sorted(self.observed_vitals.items())},
            "diagnostic_queue": self.diagnostic_queue.to_dict() if hasattr(self.diagnostic_queue, "to_dict") else None,
            "mortality_risk": round(self.mortality_risk, 6),
            "instability_index": round(self.instability_index, 6),
            "sofa_score": self.sofa_score,
            "news2_score": self.news2_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SimulationWorld":
        hidden = {}
        for k, v in d.get("hidden_state", {}).items():
            if isinstance(v, dict):
                from scrubin.clinical.cognition.diagnostics import HiddenCondition
                hidden[k] = HiddenCondition.from_dict(v) if "id" in v else v
            else:
                hidden[k] = v
        from scrubin.clinical.cognition.diagnostics import ClinicalFinding
        observable = []
        for f in d.get("observable_state", []):
            if isinstance(f, dict):
                observable.append(ClinicalFinding.from_dict(f))
            else:
                observable.append(f)
        # Reconstruct diagnostic queue if present
        dq_data = d.get("diagnostic_queue")
        if isinstance(dq_data, dict):
            from scrubin.diagnostics.queues import DiagnosticQueue, DiagnosticTask
            dq = DiagnosticQueue()
            for task_dict in dq_data.get("pending", []):
                dq.pending_tasks.append(DiagnosticTask(**task_dict))
            for task_dict in dq_data.get("completed", []):
                dq.completed_tasks.append(DiagnosticTask(**task_dict))
            # Update internal counter based on task IDs if possible
            try:
                max_id = max(int(t.id.split("-")[1]) for t in dq.pending_tasks + dq.completed_tasks)
                dq._task_counter = max_id
            except Exception:
                dq._task_counter = 0
        else:
            dq = None

        return cls(
            tick=d.get("tick", 0),
            hidden_state=hidden,
            observable_state=observable,
            physiology=PhysiologyState.from_dict(d.get("physiology", {})),
            organ_state=OrganSystemState.from_dict(d.get("organ_state", {})),
            belief_state=DiagnosticBeliefState.from_dict(d.get("belief_state", {})),
            forecast_state=ForecastState.from_dict(d.get("forecast_state", {})),
            resource_manager=ResourceManager.from_dict(d.get("resource_manager", {})),
            observed_vitals=d.get("observed_vitals", {}),
            diagnostic_queue=dq,
            mortality_risk=d.get("mortality_risk", 0.0),
            instability_index=d.get("instability_index", 0.0),
            sofa_score=d.get("sofa_score", 0),
            news2_score=d.get("news2_score", 0),
        )
    
    def evolve(self):
        from scrubin.world.coupling import SystemCouplingGraph
        from scrubin.clinical.mortality import MortalityModel
        from scrubin.clinical.scoring.sofa import SOFAScore
        from scrubin.clinical.scoring.news2 import NEWS2Score
        from scrubin.physiology.organs.cardiovascular import CardiovascularSystem
        from scrubin.physiology.organs.respiratory import RespiratorySystem
        from scrubin.physiology.organs.renal import RenalSystem

        self._prev_mortality_risk = self.mortality_risk
        self.tick += 1
        vitals = self.physiology.vitals

        cv_sys = CardiovascularSystem()
        cv_sys.state = self.organ_state.cardiovascular
        self.organ_state.cardiovascular = cv_sys.evaluate(vitals)

        resp_sys = RespiratorySystem()
        resp_sys.state = self.organ_state.respiratory
        self.organ_state.respiratory = resp_sys.evaluate(vitals)

        renal_sys = RenalSystem()
        renal_sys.state = self.organ_state.renal
        self.organ_state.renal = renal_sys.evaluate(self.organ_state.cardiovascular)

        SystemCouplingGraph.apply_organ_cascades(self)
        organ_mods = SystemCouplingGraph.evaluate_vital_influences(self)
        for key, mod in organ_mods.items():
            if key in vitals:
                vitals[key] += mod

        self.sofa_score = SOFAScore.calculate(vitals, {"renal": self.organ_state.renal})
        self.news2_score = NEWS2Score.calculate(vitals)

        self.mortality_risk = MortalityModel.evaluate(self)
