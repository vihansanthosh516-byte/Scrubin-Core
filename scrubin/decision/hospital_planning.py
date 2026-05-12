import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from scrubin.world.hospital import HospitalWorld


@dataclass
class HospitalAction:
    patient_id: str
    action: str

    def __repr__(self):
        return f"{self.patient_id}:{self.action}"


@dataclass
class HospitalPlanningState:
    hospital: HospitalWorld
    depth: int = 0
    cumulative_utility: float = 0.0
    action_history: List[HospitalAction] = field(default_factory=list)

    def clone(self) -> "HospitalPlanningState":
        return HospitalPlanningState(
            hospital=copy.deepcopy(self.hospital),
            depth=self.depth,
            cumulative_utility=self.cumulative_utility,
            action_history=list(self.action_history),
        )


@dataclass
class HospitalPlanningResult:
    actions: List[HospitalAction]
    expected_utility: float
    projected_mortality: Dict[str, float]
    projected_sofa: Dict[str, int]
    explored_nodes: int
    search_depth: int
    confidence: float
    reasoning_trace: List[str] = field(default_factory=list)


@dataclass
class HospitalSearchNode:
    state: HospitalPlanningState
    parent: Optional["HospitalSearchNode"] = None
    action: Optional[HospitalAction] = None
    children: List["HospitalSearchNode"] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0

    def uct(self, exploration_constant: float = 1.414) -> float:
        import math

        if self.visits == 0:
            return float("inf")
        if not self.parent or self.parent.visits == 0:
            return self.value / self.visits

        exploitation = self.value / self.visits
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration


class HospitalActionSpace:
    SINGLE_PATIENT_ACTIONS = {
        "airway": ["oxygen_therapy", "intubation", "bag_mask"],
        "circulation": ["iv_fluids", "blood_transfusion", "vasopressors"],
        "general": ["wait", "monitor"],
    }

    HOSPITAL_LEVEL_ACTIONS = [
        "delay_elective_surgery",
        "prioritize_icu_admission",
        "activate_overflow_protocol",
    ]

    @classmethod
    def get_actions_for_patient(
        cls, patient_id: str, world: HospitalWorld
    ) -> List[HospitalAction]:
        actions = []
        p_world = world.patients.get(patient_id)
        if p_world is None:
            return actions

        for category, act_list in cls.SINGLE_PATIENT_ACTIONS.items():
            for act in act_list:
                actions.append(HospitalAction(patient_id=patient_id, action=act))
        return actions

    @classmethod
    def get_priority_actions(
        cls, world: HospitalWorld
    ) -> List[HospitalAction]:
        actions = []
        critical_patients = []

        for pid, p_world in world.patients.items():
            if p_world.mortality_risk > 0.4 or p_world.sofa_score > 6:
                critical_patients.append(pid)

            vitals = p_world.physiology.vitals
            spo2 = vitals.get("spo2", 100)
            if spo2 < 70:
                actions.append(HospitalAction(patient_id=pid, action="intubation"))
            elif spo2 < 85:
                actions.append(HospitalAction(patient_id=pid, action="intubation"))
                actions.append(HospitalAction(patient_id=pid, action="oxygen_therapy"))

            sys_bp = vitals.get("bp_systolic", 120)
            dia_bp = vitals.get("bp_diastolic", 80)
            map_val = (sys_bp + 2 * dia_bp) / 3.0
            if map_val < 50:
                actions.append(HospitalAction(patient_id=pid, action="vasopressors"))
            elif map_val < 65:
                actions.append(HospitalAction(patient_id=pid, action="vasopressors"))
                actions.append(HospitalAction(patient_id=pid, action="iv_fluids"))

        for pid in world.patients:
            if pid not in critical_patients:
                actions.append(HospitalAction(patient_id=pid, action="wait"))
                actions.append(HospitalAction(patient_id=pid, action="monitor"))

        return actions


class HospitalMCTS:
    def __init__(self, utility_function, config=None, invariant_validator=None):
        self.utility_function = utility_function
        self.config = config or HospitalPlannerConfig()
        self.invariant_validator = invariant_validator

    def _apply_hospital_action(
        self, state: HospitalPlanningState, action: HospitalAction
    ) -> HospitalPlanningState:
        new_state = state.clone()
        new_state.depth += 1
        new_state.action_history.append(action)

        hospital = new_state.hospital

        if action.action in ("delay_elective_surgery", "prioritize_icu_admission", "activate_overflow_protocol"):
            self._apply_hospital_level_effect(hospital, action.action)
        else:
            p_world = hospital.patients.get(action.patient_id)
            if p_world:
                self._apply_patient_action(p_world, action.action)

        for _ in range(5):
            hospital.evolve()

        return new_state

    def _apply_patient_action(self, world, action: str):
        vitals = world.physiology.vitals
        if action == "intubation":
            vitals["spo2"] = min(100, vitals.get("spo2", 100) + 15)
            world.resource_manager.request_intervention_resources("intubation")
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
            world.resource_manager.request_intervention_resources("blood_transfusion")

    def _apply_hospital_level_effect(self, hospital: HospitalWorld, action: str):
        if action == "delay_elective_surgery":
            hospital.queues.pending_procedures = [
                p for p in hospital.queues.pending_procedures
                if p.action_name in ("intubation", "vasopressors", "blood_transfusion")
            ]
        elif action == "prioritize_icu_admission":
            if hospital.resources.resources.get("icu_beds"):
                hospital.resources.resources["icu_beds"].currently_used = min(
                    hospital.resources.resources["icu_beds"].total_capacity,
                    hospital.resources.resources["icu_beds"].currently_used,
                )
        elif action == "activate_overflow_protocol":
            for res_id in ("icu_beds", "staff_bandwidth"):
                if res_id in hospital.resources.resources:
                    hospital.resources.resources[res_id].total_capacity = int(
                        hospital.resources.resources[res_id].total_capacity * 1.2
                    )

    def _select(self, node: HospitalSearchNode) -> HospitalSearchNode:
        while node.children:
            node = max(node.children, key=lambda c: c.uct(self.config.exploration_constant))
        return node

    def _expand(self, node: HospitalSearchNode) -> HospitalSearchNode:
        actions = HospitalActionSpace.get_priority_actions(node.state.hospital)
        if not actions:
            actions = [HospitalAction(patient_id="*", action="wait")]

        for action in actions:
            new_state = self._apply_hospital_action(node.state, action)
            child = HospitalSearchNode(state=new_state, parent=node, action=action)
            node.children.append(child)

        import random
        return random.choice(node.children) if node.children else node

    def _rollout(self, state: HospitalPlanningState) -> float:
        current = state.clone()
        import random

        while current.depth < self.config.rollout_depth:
            actions = HospitalActionSpace.get_priority_actions(current.hospital)
            if not actions:
                actions = [HospitalAction(patient_id="*", action="wait")]

            if random.random() < 0.8:
                best = max(
                    actions,
                    key=lambda a: self._heuristic_priority(current.hospital, a),
                )
            else:
                best = random.choice(actions)

            current = self._apply_hospital_action(current, best)

            if self.invariant_validator is not None:
                for p_world in current.hospital.patients.values():
                    violations = self.invariant_validator.validate_soft(p_world)
                    if any(v.severity == "fatal" for v in violations):
                        return float("-inf")

        utility = self.utility_function.evaluate_scalar(current.hospital)
        return utility * (self.config.gamma ** current.depth)

    def _heuristic_priority(self, hospital: HospitalWorld, action: HospitalAction) -> float:
        if action.action == "intubation":
            p = hospital.patients.get(action.patient_id)
            if p and p.physiology.vitals.get("spo2", 100) < 70:
                return 100.0
        if action.action == "vasopressors":
            p = hospital.patients.get(action.patient_id)
            if p:
                sys = p.physiology.vitals.get("bp_systolic", 120)
                dia = p.physiology.vitals.get("bp_diastolic", 80)
                if (sys + 2 * dia) / 3.0 < 50:
                    return 100.0
        if action.action == "wait":
            return 0.0
        return 10.0

    def _backpropagate(self, node: HospitalSearchNode, utility: float):
        while node is not None:
            node.visits += 1
            node.value += utility
            node = node.parent

    def search(
        self, root_state: HospitalPlanningState, seed: int = 0
    ) -> Optional[HospitalPlanningResult]:
        import random
        import time

        if self.config.deterministic:
            random.seed(f"{seed}-{root_state.hospital.tick}")

        root = HospitalSearchNode(state=root_state)
        start = time.time()
        nodes_explored = 1

        for _ in range(self.config.iterations):
            if (time.time() - start) * 1000 > self.config.max_wall_time_ms:
                break
            if nodes_explored >= self.config.max_nodes:
                break

            node = self._select(root)
            if node.state.depth < self.config.max_depth:
                node = self._expand(node)
                nodes_explored += len(node.children) if node.children else 1

            utility = self._rollout(node.state)
            self._backpropagate(node, utility)

        if not root.children:
            return None

        best_child = max(root.children, key=lambda c: c.visits)
        expected_util = best_child.value / best_child.visits if best_child.visits > 0 else 0

        mortality = {
            pid: pw.mortality_risk
            for pid, pw in best_child.state.hospital.patients.items()
        }
        sofa = {
            pid: pw.sofa_score
            for pid, pw in best_child.state.hospital.patients.items()
        }

        trace = [f"Hospital-level search: best action = {best_child.action}"]
        for pid, pw in root_state.hospital.patients.items():
            trace.append(f" Patient {pid}: mortality={pw.mortality_risk:.2f} SOFA={pw.sofa_score}")

        return HospitalPlanningResult(
            actions=[best_child.action] if best_child.action else [],
            expected_utility=expected_util,
            projected_mortality=mortality,
            projected_sofa=sofa,
            explored_nodes=nodes_explored,
            search_depth=self.config.max_depth,
            confidence=float(best_child.visits) / max(1, self.config.iterations),
            reasoning_trace=trace,
        )


@dataclass
class HospitalPlannerConfig:
    enabled: bool = True
    max_depth: int = 4
    rollout_depth: int = 6
    iterations: int = 120
    max_wall_time_ms: int = 800
    max_nodes: int = 4000
    exploration_constant: float = 1.41
    gamma: float = 0.95
    deterministic: bool = True
