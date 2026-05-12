import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from scrubin.world.hospital import HospitalWorld
from scrubin.decision.hospital_utility import HospitalUtilityFunction, HospitalUtilityWeights, UtilityDecomposition
from scrubin.decision.hospital_planning import (
    HospitalAction,
    HospitalMCTS,
    HospitalPlanningResult,
    HospitalPlanningState,
    HospitalPlannerConfig,
)
from scrubin.decision.arbitration import CentralArbiter, ClinicalRecommendation, OptimizationResult
from scrubin.decision.policy_decomposition import PolicyDecomposition, DecompositionResult
from scrubin.decision.global_regret import GlobalRegretTracker, GlobalRegretSnapshot
from scrubin.agents.clinical.agents import ClinicalAgent, RespiratoryAgent, CardiologyAgent


@dataclass
class HospitalDecision:
    actions: List[HospitalAction]
    utility: float
    utility_decomp: Optional[UtilityDecomposition] = None
    regret_snapshot: Optional[GlobalRegretSnapshot] = None
    optimization_result: Optional[OptimizationResult] = None
    planning_result: Optional[HospitalPlanningResult] = None
    decomposition_results: List[DecompositionResult] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)


class HospitalDecisionEngine:
    def __init__(
        self,
        planner_config: Optional[HospitalPlannerConfig] = None,
        utility_weights: Optional[HospitalUtilityWeights] = None,
        agents: Optional[List[ClinicalAgent]] = None,
    ):
        self.planner_config = planner_config or HospitalPlannerConfig()
        self.utility_fn = HospitalUtilityFunction(utility_weights or HospitalUtilityWeights())
        self.mcts = HospitalMCTS(self.utility_fn, self.planner_config)
        self.policy_decomposition = PolicyDecomposition()
        self.regret_tracker = GlobalRegretTracker()
        self.agents = agents or [RespiratoryAgent(), CardiologyAgent()]

    def _collect_recommendations(self, hospital: HospitalWorld) -> List[ClinicalRecommendation]:
        recs = []
        for agent in self.agents:
            for patient_id, p_world in hospital.patients.items():
                agent_recs = agent.evaluate(patient_id, p_world)
                recs.extend(agent_recs)
        return recs

    def decide(self, hospital: HospitalWorld, tick: int = 0) -> HospitalDecision:
        utility_decomp = self.utility_fn.evaluate(hospital)
        current_utility = utility_decomp.total

        recs = self._collect_recommendations(hospital)

        arbiter = CentralArbiter(hospital, self.utility_fn)

        if recs:
            opt_result = arbiter.arbitrate(recs)
            arbiter_actions = [
                HospitalAction(patient_id=r.target_patient, action=r.proposed_action)
                for r in opt_result.approved
            ]
        else:
            opt_result = None
            arbiter_actions = []

        planning_result = None
        planner_actions = []

        if self.planner_config.enabled and len(hospital.patients) > 0:
            planning_state = HospitalPlanningState(hospital=hospital)
            planning_result = self.mcts.search(planning_state, seed=tick)
            if planning_result:
                planner_actions = planning_result.actions

        if planner_actions:
            final_actions = planner_actions
            method = "planner"
        elif arbiter_actions:
            final_actions = arbiter_actions
            method = "arbiter"
        else:
            available = []
            for pid in hospital.patients:
                available.append(HospitalAction(patient_id=pid, action="wait"))
            final_actions = available
            method = "fallback"

        decomp_results = []
        if final_actions:
            for action in final_actions:
                dr = self.policy_decomposition.score_action(hospital, action)
                decomp_results.append(dr)

        actions_taken = {
            a.patient_id: a.action for a in final_actions if a.patient_id != "*"
        }
        regret_snapshot = self.regret_tracker.record_snapshot(
            hospital, actions_taken, utility_fn=self.utility_fn
        )

        reasoning = [
            f"Hospital tick {tick}: utility={current_utility:.1f}, "
            f"method={method}, actions={len(final_actions)}, "
            f"regret={regret_snapshot.total_regret:.2f}"
        ]
        for dr in decomp_results:
            if dr.total_score != 0:
                reasoning.append(
                    f"  {dr.action}: score={dr.total_score:.1f} "
                    f"({', '.join(f'{k}={v:.1f}' for k, v in dr.policy_weighted.items() if v != 0)})"
                )

        return HospitalDecision(
            actions=final_actions,
            utility=current_utility,
            utility_decomp=utility_decomp,
            regret_snapshot=regret_snapshot,
            optimization_result=opt_result,
            planning_result=planning_result,
            decomposition_results=decomp_results,
            reasoning=reasoning,
        )

    @property
    def cumulative_regret(self) -> float:
        return self.regret_tracker.cumulative_regret

    @property
    def regret_history(self) -> List[GlobalRegretSnapshot]:
        return self.regret_tracker.history
