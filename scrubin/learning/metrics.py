import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import EpisodeTrajectory
from scrubin.rl.reward import RewardComponents


@dataclass
class ClinicalQualityMetrics:
    survival_rate: float = 0.0
    mean_mortality_peak: float = 0.0
    mean_mortality_final: float = 0.0
    mean_tick_count: float = 0.0
    early_intervention_rate: float = 0.0
    stabilization_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "survival_rate": round(self.survival_rate, 6),
            "mean_mortality_peak": round(self.mean_mortality_peak, 6),
            "mean_mortality_final": round(self.mean_mortality_final, 6),
            "mean_tick_count": round(self.mean_tick_count, 2),
            "early_intervention_rate": round(self.early_intervention_rate, 6),
            "stabilization_rate": round(self.stabilization_rate, 6),
        }


@dataclass
class SafetyComplianceMetrics:
    total_actions: int = 0
    violations: int = 0
    blocks: int = 0
    overrides: int = 0
    safe_action_rate: float = 0.0
    violation_rate: float = 0.0
    block_rate: float = 0.0
    override_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_actions": self.total_actions,
            "violations": self.violations,
            "blocks": self.blocks,
            "overrides": self.overrides,
            "safe_action_rate": round(self.safe_action_rate, 6),
            "violation_rate": round(self.violation_rate, 6),
            "block_rate": round(self.block_rate, 6),
            "override_rate": round(self.override_rate, 6),
        }


@dataclass
class ResourceEfficiencyMetrics:
    mean_resource_utilization: float = 0.0
    resource_waste_rate: float = 0.0
    overtreatment_rate: float = 0.0
    action_diversity: float = 0.0
    mean_actions_per_episode: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mean_resource_utilization": round(self.mean_resource_utilization, 6),
            "resource_waste_rate": round(self.resource_waste_rate, 6),
            "overtreatment_rate": round(self.overtreatment_rate, 6),
            "action_diversity": round(self.action_diversity, 6),
            "mean_actions_per_episode": round(self.mean_actions_per_episode, 2),
        }


@dataclass
class RewardDecompositionMetrics:
    mean_total: float = 0.0
    std_total: float = 0.0
    component_means: Dict[str, float] = field(default_factory=dict)
    component_stds: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mean_total": round(self.mean_total, 6),
            "std_total": round(self.std_total, 6),
            "component_means": {k: round(v, 6) for k, v in self.component_means.items()},
            "component_stds": {k: round(v, 6) for k, v in self.component_stds.items()},
        }


@dataclass
class CompositeMetrics:
    clinical: ClinicalQualityMetrics = field(default_factory=ClinicalQualityMetrics)
    safety: SafetyComplianceMetrics = field(default_factory=SafetyComplianceMetrics)
    resource: ResourceEfficiencyMetrics = field(default_factory=ResourceEfficiencyMetrics)
    reward: RewardDecompositionMetrics = field(default_factory=RewardDecompositionMetrics)
    composite_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "clinical": self.clinical.to_dict(),
            "safety": self.safety.to_dict(),
            "resource": self.resource.to_dict(),
            "reward": self.reward.to_dict(),
            "composite_score": round(self.composite_score, 6),
        }


_WEIGHTS = {
    "survival": 0.35,
    "safe_action": 0.25,
    "clinical_quality": 0.20,
    "resource_efficiency": 0.10,
    "reward_normalized": 0.10,
}


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _entropy(counts: Dict[Any, int]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p + 1e-10)
    return h


def compute_clinical_metrics(trajectories: List[EpisodeTrajectory]) -> ClinicalQualityMetrics:
    if not trajectories:
        return ClinicalQualityMetrics()
    survivals = [1.0 if t.survival else 0.0 for t in trajectories]
    mortality_peaks = []
    mortality_finals = []
    early_interventions = 0
    stabilizations = 0
    tick_counts = [float(t.tick_count) for t in trajectories]
    for t in trajectories:
        if t.mortality_curve:
            mortality_peaks.append(max(t.mortality_curve))
            mortality_finals.append(t.mortality_curve[-1])
        else:
            mortality_peaks.append(0.0)
            mortality_finals.append(0.0)
        if len(t.actions) > 0 and t.tick_count <= 3:
            non_monitor = sum(1 for a in t.actions if a != ClinicalAction.MONITOR.value and a != ClinicalAction.WAIT.value)
            if non_monitor > 0:
                early_interventions += 1
        if t.survival and t.mortality_curve and max(t.mortality_curve) > 0.3 and t.mortality_curve[-1] < 0.1:
            stabilizations += 1
    n = len(trajectories)
    return ClinicalQualityMetrics(
        survival_rate=_mean(survivals),
        mean_mortality_peak=_mean(mortality_peaks),
        mean_mortality_final=_mean(mortality_finals),
        mean_tick_count=_mean(tick_counts),
        early_intervention_rate=early_interventions / n if n else 0.0,
        stabilization_rate=stabilizations / n if n else 0.0,
    )


def compute_safety_metrics(
    trajectories: List[EpisodeTrajectory],
    num_violations: int = 0,
    num_blocks: int = 0,
    num_overrides: int = 0,
) -> SafetyComplianceMetrics:
    total_actions = sum(len(t.actions) for t in trajectories)
    if total_actions == 0:
        return SafetyComplianceMetrics()
    return SafetyComplianceMetrics(
        total_actions=total_actions,
        violations=num_violations,
        blocks=num_blocks,
        overrides=num_overrides,
        safe_action_rate=round((total_actions - num_violations) / total_actions, 6),
        violation_rate=round(num_violations / total_actions, 6),
        block_rate=round(num_blocks / total_actions, 6),
        override_rate=round(num_overrides / total_actions, 6),
    )


def compute_resource_metrics(trajectories: List[EpisodeTrajectory]) -> ResourceEfficiencyMetrics:
    if not trajectories:
        return ResourceEfficiencyMetrics()
    action_counts: Dict[int, int] = {}
    total_actions = 0
    invasive_count = 0
    for t in trajectories:
        for a in t.actions:
            action_counts[a] = action_counts.get(a, 0) + 1
            total_actions += 1
            if a in (ClinicalAction.INTUBATE.value, ClinicalAction.VASOPRESSORS.value,
                     ClinicalAction.EMERGENCY_AIRWAY.value, ClinicalAction.SURGICAL_INTERVENTION.value):
                invasive_count += 1
    n = len(trajectories)
    max_entropy = math.log2(len(ClinicalAction)) if len(ClinicalAction) > 1 else 1.0
    diversity = _entropy(action_counts) / max_entropy if max_entropy > 0 else 0.0
    return ResourceEfficiencyMetrics(
        overtreatment_rate=invasive_count / total_actions if total_actions else 0.0,
        action_diversity=diversity,
        mean_actions_per_episode=total_actions / n if n else 0.0,
    )


def compute_reward_metrics(total_rewards: List[float]) -> RewardDecompositionMetrics:
    if not total_rewards:
        return RewardDecompositionMetrics()
    return RewardDecompositionMetrics(
        mean_total=_mean(total_rewards),
        std_total=_std(total_rewards),
    )


def compute_composite_score(
    clinical: ClinicalQualityMetrics,
    safety: SafetyComplianceMetrics,
    resource: ResourceEfficiencyMetrics,
    reward: RewardDecompositionMetrics,
) -> float:
    survival_score = clinical.survival_rate
    safe_score = safety.safe_action_rate if safety.total_actions > 0 else 1.0
    clinical_quality = 1.0 - min(1.0, clinical.mean_mortality_final)
    resource_score = 1.0 - min(1.0, resource.overtreatment_rate)
    reward_norm = max(0.0, min(1.0, (reward.mean_total + 10.0) / 20.0))
    composite = (
        _WEIGHTS["survival"] * survival_score
        + _WEIGHTS["safe_action"] * safe_score
        + _WEIGHTS["clinical_quality"] * clinical_quality
        + _WEIGHTS["resource_efficiency"] * resource_score
        + _WEIGHTS["reward_normalized"] * reward_norm
    )
    return round(composite, 6)


def compute_all_metrics(
    trajectories: List[EpisodeTrajectory],
    num_violations: int = 0,
    num_blocks: int = 0,
    num_overrides: int = 0,
    total_rewards: List[float] | None = None,
) -> CompositeMetrics:
    clinical = compute_clinical_metrics(trajectories)
    safety = compute_safety_metrics(trajectories, num_violations, num_blocks, num_overrides)
    resource = compute_resource_metrics(trajectories)
    rewards = total_rewards or [t.total_reward for t in trajectories]
    reward = compute_reward_metrics(rewards)
    composite_score = compute_composite_score(clinical, safety, resource, reward)
    return CompositeMetrics(
        clinical=clinical,
        safety=safety,
        resource=resource,
        reward=reward,
        composite_score=composite_score,
    )
