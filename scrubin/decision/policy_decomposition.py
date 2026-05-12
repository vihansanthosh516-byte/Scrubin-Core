from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.hospital import HospitalWorld
from scrubin.world.model import SimulationWorld
from scrubin.decision.hospital_planning import HospitalAction


@dataclass
class PolicyScore:
    action: HospitalAction
    policy_name: str
    raw_score: float
    weight: float

    @property
    def weighted_score(self) -> float:
        return self.raw_score * self.weight


class SubPolicy(ABC):
    name: str = "base"
    weight: float = 1.0

    @abstractmethod
    def score_action(
        self, hospital: HospitalWorld, action: HospitalAction
    ) -> float:
        ...


class TriagePolicy(SubPolicy):
    name = "triage"
    weight = 1.5

    def score_action(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        p_world = hospital.patients.get(action.patient_id)
        if p_world is None:
            return 0.0

        mortality = p_world.mortality_risk
        sofa = p_world.sofa_score

        if action.action in ("intubation", "vasopressors"):
            if mortality > 0.6:
                return 20.0
            elif mortality > 0.3:
                return 10.0
            return -5.0

        if action.action == "wait":
            if mortality < 0.1 and sofa < 4:
                return 5.0
            return -15.0

        if action.action == "monitor":
            if mortality < 0.2:
                return 3.0
            return -10.0

        return 0.0


class RespiratoryPolicy(SubPolicy):
    name = "respiratory"
    weight = 1.3

    def score_action(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        p_world = hospital.patients.get(action.patient_id)
        if p_world is None:
            return 0.0

        spo2 = p_world.physiology.vitals.get("spo2", 100)

        if action.action == "intubation":
            if spo2 < 70:
                return 50.0
            elif spo2 < 85:
                return 25.0
            return -20.0

        if action.action == "oxygen_therapy":
            if spo2 < 92:
                return 15.0
            if spo2 >= 97:
                return -5.0
            return 5.0

        if action.action == "bag_mask":
            if spo2 < 70:
                return 30.0
            return -10.0

        return 0.0


class CardiovascularPolicy(SubPolicy):
    name = "cardiovascular"
    weight = 1.3

    def score_action(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        p_world = hospital.patients.get(action.patient_id)
        if p_world is None:
            return 0.0

        vitals = p_world.physiology.vitals
        sys_bp = vitals.get("bp_systolic", 120)
        dia_bp = vitals.get("bp_diastolic", 80)
        map_val = (sys_bp + 2 * dia_bp) / 3.0

        if action.action == "vasopressors":
            if map_val < 50:
                return 50.0
            elif map_val < 65:
                return 20.0
            return -20.0

        if action.action == "iv_fluids":
            if map_val < 65:
                return 15.0
            if map_val > 90:
                return -5.0
            return 5.0

        if action.action == "blood_transfusion":
            if map_val < 55:
                return 25.0
            return -10.0

        return 0.0


class ResourceAllocationPolicy(SubPolicy):
    name = "resource_allocation"
    weight = 1.0

    def score_action(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        scarce_actions = {
            "intubation": ("ventilators", 1),
            "ventilator_support": ("ventilators", 1),
            "blood_transfusion": ("blood_units", 2),
            "surgical_intervention": ("icu_beds", 1),
        }

        if action.action not in scarce_actions:
            return 0.0

        res_type, amount = scarce_actions[action.action]
        res_state = hospital.resources.resources.get(res_type)
        if res_state is None:
            return -100.0

        available = res_state.available
        if available < amount:
            return -200.0

        scarcity_ratio = available / max(1, res_state.total_capacity)
        if scarcity_ratio < 0.1:
            return -30.0
        elif scarcity_ratio < 0.3:
            return -10.0

        return 0.0


class EthicsConstraintPolicy(SubPolicy):
    name = "ethics_constraint"
    weight = 0.8

    def score_action(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        p_world = hospital.patients.get(action.patient_id)
        if p_world is None:
            return 0.0

        if action.action in ("intubation", "vasopressors", "surgical_intervention"):
            if p_world.mortality_risk > 0.9 and p_world.sofa_score >= 12:
                return -50.0
            if p_world.mortality_risk > 0.8 and p_world.sofa_score >= 10:
                return -20.0

        return 0.0


@dataclass
class DecompositionResult:
    action: HospitalAction
    total_score: float
    policy_scores: Dict[str, float] = field(default_factory=dict)
    policy_weighted: Dict[str, float] = field(default_factory=dict)


class PolicyDecomposition:
    def __init__(self, policies: Optional[List[SubPolicy]] = None):
        self.policies = policies or [
            TriagePolicy(),
            RespiratoryPolicy(),
            CardiovascularPolicy(),
            ResourceAllocationPolicy(),
            EthicsConstraintPolicy(),
        ]

    def score_action(
        self, hospital: HospitalWorld, action: HospitalAction
    ) -> DecompositionResult:
        result = DecompositionResult(action=action, total_score=0.0)

        for policy in self.policies:
            raw = policy.score_action(hospital, action)
            weighted = raw * policy.weight
            result.policy_scores[policy.name] = raw
            result.policy_weighted[policy.name] = weighted
            result.total_score += weighted

        return result

    def select_best(
        self, hospital: HospitalWorld, actions: List[HospitalAction]
    ) -> DecompositionResult:
        if not actions:
            return DecompositionResult(
                action=HospitalAction(patient_id="*", action="wait"),
                total_score=0.0,
            )

        scored = [self.score_action(hospital, a) for a in actions]
        return max(scored, key=lambda r: r.total_score)

    def rank_actions(
        self, hospital: HospitalWorld, actions: List[HospitalAction]
    ) -> List[DecompositionResult]:
        scored = [self.score_action(hospital, a) for a in actions]
        return sorted(scored, key=lambda r: r.total_score, reverse=True)
