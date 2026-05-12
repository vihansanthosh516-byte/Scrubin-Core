from dataclasses import dataclass, field
from typing import Dict, List

from scrubin.world.hospital import HospitalWorld
from scrubin.world.model import SimulationWorld


@dataclass
class HospitalUtilityWeights:
    survival_weight: float = 100.0
    organ_preservation_weight: float = 20.0
    resource_efficiency_weight: float = 5.0
    stability_weight: float = 10.0
    staff_fatigue_weight: float = 8.0
    outbreak_weight: float = 15.0
    queue_delay_weight: float = 3.0
    fairness_weight: float = 12.0
    intervention_cost_weight: float = 2.0


@dataclass
class UtilityDecomposition:
    total: float = 0.0
    survival_gain: float = 0.0
    mortality_risk_penalty: float = 0.0
    organ_preservation_gain: float = 0.0
    resource_penalty: float = 0.0
    staff_fatigue_penalty: float = 0.0
    outbreak_penalty: float = 0.0
    queue_delay_penalty: float = 0.0
    fairness_reward: float = 0.0
    intervention_cost_penalty: float = 0.0
    per_patient: Dict[str, float] = field(default_factory=dict)


class HospitalUtilityFunction:
    def __init__(self, weights: HospitalUtilityWeights = None):
        self.weights = weights or HospitalUtilityWeights()

    def evaluate_patient(self, world: SimulationWorld) -> float:
        w = self.weights
        survival_prob = 1.0 - world.mortality_risk
        survival_gain = survival_prob * w.survival_weight

        organs = world.organ_state
        organ_health_avg = (
            organs.cardiovascular.health
            + organs.respiratory.health
            + organs.renal.health
        ) / 3.0
        organ_gain = organ_health_avg * w.organ_preservation_weight

        used_resources = sum(
            r.currently_used for r in world.resource_manager.resources.values()
        )
        resource_penalty = used_resources * w.resource_efficiency_weight

        instability = world.sofa_score + world.news2_score
        instability_penalty = instability * w.stability_weight

        return survival_gain + organ_gain - resource_penalty - instability_penalty

    def evaluate(self, hospital: HospitalWorld) -> UtilityDecomposition:
        w = self.weights
        decomp = UtilityDecomposition()

        total_survival = 0.0
        total_mortality = 0.0
        total_organ = 0.0
        total_resource = 0.0
        total_intervention_cost = 0.0

        patient_utilities: List[float] = []

        for patient_id, p_world in hospital.patients.items():
            p_util = self.evaluate_patient(p_world)
            decomp.per_patient[patient_id] = p_util

            survival_prob = 1.0 - p_world.mortality_risk
            total_survival += survival_prob * w.survival_weight
            total_mortality += p_world.mortality_risk * w.survival_weight

            organs = p_world.organ_state
            organ_avg = (
                organs.cardiovascular.health
                + organs.respiratory.health
                + organs.renal.health
            ) / 3.0
            total_organ += organ_avg * w.organ_preservation_weight

            used = sum(
                r.currently_used
                for r in p_world.resource_manager.resources.values()
            )
            total_resource += used * w.resource_efficiency_weight

            total_intervention_cost += len(p_world.physiology.active_trajectories) * w.intervention_cost_weight

            patient_utilities.append(p_util)

        decomp.survival_gain = total_survival
        decomp.mortality_risk_penalty = total_mortality
        decomp.organ_preservation_gain = total_organ
        decomp.resource_penalty = total_resource
        decomp.intervention_cost_penalty = total_intervention_cost

        staff_fatigue = hospital.staff.team_fatigue.fatigue_level
        staff_overload = hospital.staff.team_fatigue.cognitive_overload
        decomp.staff_fatigue_penalty = (
            (staff_fatigue + staff_overload) * w.staff_fatigue_weight
            * len(hospital.patients)
        )

        outbreak_severity = sum(
            p.severity for p in hospital.outbreaks.active_pressures.values()
        )
        contamination = hospital.outbreaks.icu_contamination_level
        decomp.outbreak_penalty = (
            (outbreak_severity + contamination) * w.outbreak_weight
        )

        pending = len(hospital.queues.pending_procedures)
        emergency = len(hospital.queues.emergency_queue)
        decomp.queue_delay_penalty = (pending + emergency * 3) * w.queue_delay_weight

        if len(patient_utilities) > 1:
            mean_util = sum(patient_utilities) / len(patient_utilities)
            variance = sum((u - mean_util) ** 2 for u in patient_utilities) / len(
                patient_utilities
            )
            decomp.fairness_reward = max(0.0, 1.0 - variance / max(1.0, mean_util**2)) * w.fairness_weight * len(
                hospital.patients
            )

        decomp.total = (
            decomp.survival_gain
            + decomp.organ_preservation_gain
            - decomp.mortality_risk_penalty
            - decomp.resource_penalty
            - decomp.staff_fatigue_penalty
            - decomp.outbreak_penalty
            - decomp.queue_delay_penalty
            + decomp.fairness_reward
            - decomp.intervention_cost_penalty
        )

        return decomp

    def evaluate_scalar(self, hospital: HospitalWorld) -> float:
        return self.evaluate(hospital).total
