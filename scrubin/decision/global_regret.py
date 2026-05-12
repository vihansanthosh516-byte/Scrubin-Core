from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.hospital import HospitalWorld


@dataclass
class ResourceRegretEntry:
    resource_type: str
    tick: int
    allocated_to: str
    alternative_patient: str
    allocated_utility: float
    alternative_utility: float
    regret: float


@dataclass
class PatientRegretEntry:
    patient_id: str
    tick: int
    action_taken: str
    best_hindsight_action: str
    utility_realized: float
    best_hindsight_utility: float
    regret: float
    died_suboptimally: bool = False


@dataclass
class GlobalRegretSnapshot:
    tick: int
    total_regret: float = 0.0
    resource_regret: float = 0.0
    patient_regret: float = 0.0
    icu_utilization_regret: float = 0.0
    fairness_regret: float = 0.0
    resource_regret_entries: List[ResourceRegretEntry] = field(default_factory=list)
    patient_regret_entries: List[PatientRegretEntry] = field(default_factory=list)


class GlobalRegretTracker:
    def __init__(self):
        self._history: List[GlobalRegretSnapshot] = []
        self._cumulative_regret: float = 0.0

    def compute_resource_regret(
        self,
        hospital: HospitalWorld,
        allocation_map: Dict[str, str],
        utility_fn=None,
    ) -> List[ResourceRegretEntry]:
        entries = []
        if utility_fn is None:
            from scrubin.decision.hospital_utility import HospitalUtilityFunction
            utility_fn = HospitalUtilityFunction()

        scarce_resources = {}
        for res_id, res_state in hospital.resources.resources.items():
            if res_state.total_capacity > 0 and res_state.currently_used > 0:
                scarce_resources[res_id] = res_state

        for res_type, res_state in scarce_resources.items():
            allocated_patients = [
                pid for pid, rid in allocation_map.items() if rid == res_type
            ]

            for alt_pid, alt_world in hospital.patients.items():
                if alt_pid in allocated_patients:
                    continue

                if allocated_patients:
                    current_util = utility_fn.evaluate_patient(
                        hospital.patients.get(allocated_patients[0], alt_world)
                    )
                else:
                    current_util = 0.0
                alt_util = utility_fn.evaluate_patient(alt_world)
                regret = max(0.0, alt_util - current_util)

                if regret > 0.01:
                    entries.append(
                        ResourceRegretEntry(
                            resource_type=res_type,
                            tick=hospital.tick,
                            allocated_to=allocated_patients[0] if allocated_patients else "none",
                            alternative_patient=alt_pid,
                            allocated_utility=current_util,
                            alternative_utility=alt_util,
                            regret=regret,
                        )
                    )

        return entries

    def compute_patient_regret(
        self,
        hospital: HospitalWorld,
        actions_taken: Dict[str, str],
        utility_fn=None,
    ) -> List[PatientRegretEntry]:
        entries = []
        if utility_fn is None:
            from scrubin.decision.hospital_utility import HospitalUtilityFunction
            utility_fn = HospitalUtilityFunction()

        candidate_actions = [
            "intubation", "oxygen_therapy", "bag_mask",
            "vasopressors", "iv_fluids", "blood_transfusion",
            "wait", "monitor",
        ]

        for pid, p_world in hospital.patients.items():
            action_taken = actions_taken.get(pid, "wait")
            current_util = utility_fn.evaluate_patient(p_world)

            best_action = action_taken
            best_util = current_util

            for alt_action in candidate_actions:
                trial_world = self._simulate_action(p_world, alt_action)
                trial_util = utility_fn.evaluate_patient(trial_world)
                if trial_util > best_util:
                    best_util = trial_util
                    best_action = alt_action

            regret = max(0.0, best_util - current_util)
            died_subopt = (
                p_world.mortality_risk > 0.8
                and action_taken in ("wait", "monitor")
                and best_action not in ("wait", "monitor")
            )

            entries.append(
                PatientRegretEntry(
                    patient_id=pid,
                    tick=hospital.tick,
                    action_taken=action_taken,
                    best_hindsight_action=best_action,
                    utility_realized=current_util,
                    best_hindsight_utility=best_util,
                    regret=regret,
                    died_suboptimally=died_subopt,
                )
            )

        return entries

    def compute_icu_utilization_regret(self, hospital: HospitalWorld) -> float:
        icu_beds = hospital.resources.resources.get("icu_beds")
        if icu_beds is None:
            return 0.0

        utilization = icu_beds.currently_used / max(1, icu_beds.total_capacity)
        critical_without_icu = 0

        for pid, p_world in hospital.patients.items():
            if p_world.sofa_score > 6 and p_world.mortality_risk > 0.3:
                critical_without_icu += 1

        if critical_without_icu > 0 and utilization >= 1.0:
            return critical_without_icu * 15.0
        if utilization < 0.5:
            return -2.0
        return 0.0

    def compute_fairness_regret(self, hospital: HospitalWorld, utility_fn=None) -> float:
        if utility_fn is None:
            from scrubin.decision.hospital_utility import HospitalUtilityFunction
            utility_fn = HospitalUtilityFunction()

        if len(hospital.patients) < 2:
            return 0.0

        utils = [
            utility_fn.evaluate_patient(pw)
            for pw in hospital.patients.values()
        ]
        mean = sum(utils) / len(utils)
        if mean == 0:
            return 0.0

        variance = sum((u - mean) ** 2 for u in utils) / len(utils)
        return variance / (mean ** 2) * 10.0

    def record_snapshot(
        self,
        hospital: HospitalWorld,
        actions_taken: Dict[str, str],
        allocation_map: Optional[Dict[str, str]] = None,
        utility_fn=None,
    ) -> GlobalRegretSnapshot:
        if utility_fn is None:
            from scrubin.decision.hospital_utility import HospitalUtilityFunction
            utility_fn = HospitalUtilityFunction()

        resource_entries = self.compute_resource_regret(
            hospital, allocation_map or {}, utility_fn
        )
        patient_entries = self.compute_patient_regret(
            hospital, actions_taken, utility_fn
        )

        resource_regret = sum(e.regret for e in resource_entries)
        patient_regret = sum(e.regret for e in patient_entries)
        icu_regret = self.compute_icu_utilization_regret(hospital)
        fairness_regret = self.compute_fairness_regret(hospital, utility_fn)

        total = resource_regret + patient_regret + icu_regret + fairness_regret

        snapshot = GlobalRegretSnapshot(
            tick=hospital.tick,
            total_regret=total,
            resource_regret=resource_regret,
            patient_regret=patient_regret,
            icu_utilization_regret=icu_regret,
            fairness_regret=fairness_regret,
            resource_regret_entries=resource_entries,
            patient_regret_entries=patient_entries,
        )

        self._history.append(snapshot)
        self._cumulative_regret += total

        return snapshot

    @property
    def history(self) -> List[GlobalRegretSnapshot]:
        return list(self._history)

    @property
    def cumulative_regret(self) -> float:
        return self._cumulative_regret

    @property
    def average_regret(self) -> float:
        if not self._history:
            return 0.0
        return self._cumulative_regret / len(self._history)

    def regret_by_category(self) -> Dict[str, float]:
        if not self._history:
            return {}
        return {
            "resource": sum(s.resource_regret for s in self._history),
            "patient": sum(s.patient_regret for s in self._history),
            "icu_utilization": sum(s.icu_utilization_regret for s in self._history),
            "fairness": sum(s.fairness_regret for s in self._history),
        }

    def _simulate_action(self, world, action: str):
        import copy

        trial = copy.deepcopy(world)
        vitals = trial.physiology.vitals

        if action == "intubation":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 15)
        elif action == "oxygen_therapy":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 5)
        elif action == "bag_mask":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 8)
        elif action == "vasopressors":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 20
            vitals["heart_rate"] = vitals.get("heart_rate", 80) + 10
        elif action == "iv_fluids":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 5
        elif action == "blood_transfusion":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 10
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 5)

        trial.mortality_risk = max(0.0, trial.mortality_risk - 0.05)
        return trial
