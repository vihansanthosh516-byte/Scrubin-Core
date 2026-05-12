import copy
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

from scrubin.decision.hospital_utility import HospitalUtilityFunction
from scrubin.world.hospital import HospitalWorld


@dataclass
class ClinicalRecommendation:
    id: str
    agent_id: str
    target_patient: str
    proposed_action: str

    expected_utility: float
    urgency: float
    resource_cost: float
    confidence: float

    reasoning: List[str] = field(default_factory=list)


@dataclass
class ActionSet:
    actions: Tuple[ClinicalRecommendation, ...]
    utility: float = 0.0
    feasible: bool = True
    rejected: List[ClinicalRecommendation] = field(default_factory=list)


@dataclass
class OptimizationResult:
    approved: List[ClinicalRecommendation]
    rejected: List[ClinicalRecommendation]
    global_utility: float
    utility_decomp: Optional[object] = None
    action_sets_evaluated: int = 0
    optimization_method: str = "greedy"


class CentralArbiter:
    def __init__(self, hospital_world: HospitalWorld, utility_fn: HospitalUtilityFunction = None):
        self.hospital = hospital_world
        self.utility_fn = utility_fn or HospitalUtilityFunction()

    def _resource_requirements(self, action: str) -> Dict[str, int]:
        if action in ("intubation", "ventilator_support"):
            return {"ventilators": 1, "staff_bandwidth": 15}
        elif action == "blood_transfusion":
            return {"blood_units": 2, "staff_bandwidth": 10}
        elif action == "surgical_intervention":
            return {"icu_beds": 1, "staff_bandwidth": 40}
        return {}

    def _check_feasibility(
        self,
        action_set: List[ClinicalRecommendation],
        available: Dict[str, int],
    ) -> Tuple[bool, Dict[str, int]]:
        simulated = dict(available)
        for rec in action_set:
            for res, amount in self._resource_requirements(rec.proposed_action).items():
                if simulated.get(res, 0) < amount:
                    return False, available
                simulated[res] -= amount
        return True, simulated

    def _evaluate_action_set(
        self,
        action_set: List[ClinicalRecommendation],
        hospital: HospitalWorld,
    ) -> float:
        trial = copy.deepcopy(hospital)
        for rec in action_set:
            p_world = trial.patients.get(rec.target_patient)
            if p_world is None:
                continue
            self._apply_recommendation_effect(p_world, rec.proposed_action)
            trial.resources.request_intervention_resources(rec.proposed_action)
        return self.utility_fn.evaluate_scalar(trial)

    def _apply_recommendation_effect(self, world, action: str):
        vitals = world.physiology.vitals
        if action == "intubation":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 15)
        elif action == "oxygen_therapy":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 5)
        elif action == "vasopressors":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 20
            vitals["heart_rate"] = vitals.get("heart_rate", 80) + 10
        elif action == "iv_fluids":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 5
        elif action == "blood_transfusion":
            vitals["bp_systolic"] = vitals.get("bp_systolic", 120) + 10
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 5)

    def arbitrate(
        self,
        recommendations: List[ClinicalRecommendation],
        method: str = "greedy",
    ) -> OptimizationResult:
        if method == "exhaustive" and len(recommendations) <= 12:
            return self._arbitrate_exhaustive(recommendations)
        return self._arbitrate_greedy(recommendations)

    def _arbitrate_greedy(
        self, recommendations: List[ClinicalRecommendation]
    ) -> OptimizationResult:
        available = {
            res_id: res.available
            for res_id, res in self.hospital.resources.resources.items()
        }

        def sort_key(rec: ClinicalRecommendation):
            efficiency = rec.expected_utility / max(0.1, rec.resource_cost)
            return (rec.urgency, efficiency)

        sorted_recs = sorted(recommendations, key=sort_key, reverse=True)

        approved = []
        rejected = []
        for rec in sorted_recs:
            reqs = self._resource_requirements(rec.proposed_action)
            feasible = True
            for res, amount in reqs.items():
                if available.get(res, 0) < amount:
                    feasible = False
                    break

            if not feasible:
                rejected.append(rec)
                continue

            for res, amount in reqs.items():
                available[res] -= amount
            approved.append(rec)

        best_set = self._resolve_patient_conflicts(approved, sort_key)

        utility = self._evaluate_action_set(best_set, self.hospital)

        all_approved_ids = {r.id for r in best_set}
        final_rejected = [r for r in recommendations if r.id not in all_approved_ids]

        return OptimizationResult(
            approved=best_set,
            rejected=final_rejected,
            global_utility=utility,
            action_sets_evaluated=len(sorted_recs),
            optimization_method="greedy",
        )

    def _resolve_patient_conflicts(
        self,
        approved: List[ClinicalRecommendation],
        sort_key,
    ) -> List[ClinicalRecommendation]:
        patient_actions: Dict[str, ClinicalRecommendation] = {}
        final = []

        for rec in approved:
            existing = patient_actions.get(rec.target_patient)
            if existing is None:
                patient_actions[rec.target_patient] = rec
                final.append(rec)
            elif sort_key(rec) > sort_key(existing):
                final.remove(existing)
                final.append(rec)
                patient_actions[rec.target_patient] = rec

        return final

    def _arbitrate_exhaustive(
        self, recommendations: List[ClinicalRecommendation]
    ) -> OptimizationResult:
        available = {
            res_id: res.available
            for res_id, res in self.hospital.resources.resources.items()
        }

        best_utility = -float("inf")
        best_set: List[ClinicalRecommendation] = []
        best_rejected: List[ClinicalRecommendation] = []
        sets_evaluated = 0

        conflict_groups = self._group_by_patient(recommendations)

        patient_choices: List[List[Optional[ClinicalRecommendation]]] = []
        for patient_id, recs in conflict_groups.items():
            options: List[Optional[ClinicalRecommendation]] = [None]
            for r in recs:
                options.append(r)
            patient_choices.append(options)

        for combo in itertools.product(*patient_choices):
            action_set = [r for r in combo if r is not None]
            feasible, _ = self._check_feasibility(action_set, available)
            if not feasible:
                sets_evaluated += 1
                continue

            utility = self._evaluate_action_set(action_set, self.hospital)
            sets_evaluated += 1

            if utility > best_utility:
                best_utility = utility
                best_set = action_set

        approved_ids = {r.id for r in best_set}
        rejected = [r for r in recommendations if r.id not in approved_ids]

        return OptimizationResult(
            approved=best_set,
            rejected=rejected,
            global_utility=best_utility,
            action_sets_evaluated=sets_evaluated,
            optimization_method="exhaustive",
        )

    def _group_by_patient(
        self, recommendations: List[ClinicalRecommendation]
    ) -> Dict[str, List[ClinicalRecommendation]]:
        groups: Dict[str, List[ClinicalRecommendation]] = {}
        for rec in recommendations:
            groups.setdefault(rec.target_patient, []).append(rec)
        return groups
