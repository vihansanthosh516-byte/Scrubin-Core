from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from scrubin.world.model import SimulationWorld
from scrubin.clinical.resources import ResourceManager
from scrubin.clinical.staff import StaffSystemState
from scrubin.clinical.scheduling import QueueState
from scrubin.clinical.environment import OutbreakState


@dataclass
class HospitalTelemetry:
    total_mortality_risk_aggregate: float = 0.0
    icu_utilization_ratio: float = 0.0
    ventilator_utilization_ratio: float = 0.0
    staff_overload_index: float = 0.0
    active_critical_alerts: int = 0

    def to_dict(self) -> dict:
        return {
            "total_mortality_risk_aggregate": round(self.total_mortality_risk_aggregate, 6),
            "icu_utilization_ratio": round(self.icu_utilization_ratio, 6),
            "ventilator_utilization_ratio": round(self.ventilator_utilization_ratio, 6),
            "staff_overload_index": round(self.staff_overload_index, 6),
            "active_critical_alerts": self.active_critical_alerts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HospitalTelemetry":
        return cls(
            total_mortality_risk_aggregate=d.get("total_mortality_risk_aggregate", 0.0),
            icu_utilization_ratio=d.get("icu_utilization_ratio", 0.0),
            ventilator_utilization_ratio=d.get("ventilator_utilization_ratio", 0.0),
            staff_overload_index=d.get("staff_overload_index", 0.0),
            active_critical_alerts=d.get("active_critical_alerts", 0),
        )


@dataclass
class HospitalWorld:
    tick: int = 0

    patients: Dict[str, SimulationWorld] = field(default_factory=dict)

    resources: ResourceManager = field(default_factory=ResourceManager)

    staff: StaffSystemState = field(default_factory=StaffSystemState)

    queues: QueueState = field(default_factory=QueueState)

    outbreaks: OutbreakState = field(default_factory=OutbreakState)

    telemetry: HospitalTelemetry = field(default_factory=HospitalTelemetry)

    _transaction_manager: Any = None

    def to_dict(self) -> dict:
        patients = {}
        for pid in sorted(self.patients.keys()):
            patients[pid] = self.patients[pid].to_dict()
        return {
            "tick": self.tick,
            "patients": patients,
            "resources": self.resources.to_dict(),
            "staff": self.staff.to_dict(),
            "queues": self.queues.to_dict(),
            "outbreaks": self.outbreaks.to_dict(),
            "telemetry": self.telemetry.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HospitalWorld":
        patients = {}
        for pid, pw in d.get("patients", {}).items():
            patients[pid] = SimulationWorld.from_dict(pw) if isinstance(pw, dict) else pw
        return cls(
            tick=d.get("tick", 0),
            patients=patients,
            resources=ResourceManager.from_dict(d.get("resources", {})),
            staff=StaffSystemState.from_dict(d.get("staff", {})),
            queues=QueueState.from_dict(d.get("queues", {})),
            outbreaks=OutbreakState.from_dict(d.get("outbreaks", {})),
            telemetry=HospitalTelemetry.from_dict(d.get("telemetry", {})),
        )

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_transaction_manager", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._transaction_manager = None

    @property
    def transaction_manager(self):
        if self._transaction_manager is None:
            from scrubin.clinical.resources_transactions import TransactionalResourceManager
            self._transaction_manager = TransactionalResourceManager(
                base_manager=self.resources, tick=self.tick
            )
        return self._transaction_manager

    def evolve(self):
        self.tick += 1

        if self._transaction_manager is not None:
            self._transaction_manager.set_tick(self.tick)
            self._transaction_manager.expire_stale(self.tick)

        active_critical = 0
        total_mortality = 0.0
        for patient_id, p_world in self.patients.items():
            p_world.evolve()
            total_mortality += p_world.mortality_risk
            if p_world.mortality_risk > 0.4 or p_world.sofa_score > 6:
                active_critical += 1

        self.outbreaks.evolve()

        self.staff.adjust_overload(active_critical)
        self.staff.evolve()

        completed_procedures = self.queues.evolve()

        self.telemetry.total_mortality_risk_aggregate = total_mortality
        self.telemetry.active_critical_alerts = active_critical

        icu_beds = self.resources.resources.get("icu_beds")
        self.telemetry.icu_utilization_ratio = (
            icu_beds.currently_used / max(1, icu_beds.total_capacity)
            if icu_beds else 0.0
        )

        vents = self.resources.resources.get("ventilators")
        self.telemetry.ventilator_utilization_ratio = (
            vents.currently_used / max(1, vents.total_capacity)
            if vents else 0.0
        )

        self.telemetry.staff_overload_index = self.staff.team_fatigue.cognitive_overload
