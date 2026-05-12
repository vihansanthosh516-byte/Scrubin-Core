import math
import random
import time
from typing import Optional, Tuple
from dataclasses import dataclass, field

from scrubin.decision.planning import PlanningState
from scrubin.decision.utility import UtilityFunction
from scrubin.decision.config import PlannerConfig
from scrubin.decision.result import PlanningResult

@dataclass
class SearchNode:
    state: PlanningState
    parent: Optional["SearchNode"] = None
    action: Optional[str] = None
    
    children: list["SearchNode"] = field(default_factory=list)
    
    visits: int = 0
    value: float = 0.0
    
    def uct(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float('inf')
        if not self.parent or self.parent.visits == 0:
            return self.value / self.visits
            
        exploitation = self.value / self.visits
        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

class MonteCarloTreeSearch:
    def __init__(self, utility_function: UtilityFunction, config: PlannerConfig, invariant_validator=None):
        self.utility_function = utility_function
        self.config = config
        self.invariant_validator = invariant_validator

    def _get_action_hierarchy(self, state: PlanningState) -> dict:
        return {
            "airway": ["oxygen_therapy", "intubation", "bag_mask"],
            "circulation": ["iv_fluids", "blood_transfusion", "vasopressors"],
            "general": ["wait", "monitor"]
        }

    def _get_available_actions(self, state: PlanningState, category: str = None) -> list[str]:
        hierarchy = self._get_action_hierarchy(state)
        if category and category in hierarchy:
            return hierarchy[category]
        return list(hierarchy.keys())

    def _apply_action(self, state: PlanningState, action: str) -> PlanningState:
        new_state = state.clone()
        new_state.depth += 1
        new_state.action_history.append(action)
        
        # Advance world by 5 ticks (a standard simulation step block)
        for _ in range(5):
            new_state.world.evolve()
            
        # Apply deterministic heuristic effects
        if action == "intubation":
            new_state.world.physiology.vitals["spo2"] = min(100, new_state.world.physiology.vitals.get("spo2", 100) + 15)
            new_state.world.resource_manager.request_intervention_resources("intubation")
        elif action == "vasopressors":
            new_state.world.physiology.vitals["bp_systolic"] += 20
            new_state.world.physiology.vitals["heart_rate"] += 10
        elif action == "iv_fluids":
            new_state.world.physiology.vitals["bp_systolic"] += 5
        elif action == "blood_transfusion":
            new_state.world.physiology.vitals["bp_systolic"] += 10
            new_state.world.physiology.vitals["spo2"] += 5
            new_state.world.resource_manager.request_intervention_resources("blood_transfusion")
            
        return new_state

    def search(self, root_state: PlanningState, seed: int = 0) -> Optional[PlanningResult]:
        if not self.config.enabled:
            return None

        if self.config.emergency_bypass:
            from scrubin.decision.interrupts import EmergencyInterrupts
            interrupt_action = EmergencyInterrupts.check_interrupt(root_state.world)
            if interrupt_action:
                return PlanningResult(
                    selected_action=interrupt_action,
                    expected_utility=0.0,
                    projected_mortality=root_state.world.mortality_risk,
                    projected_sofa=root_state.world.sofa_score,
                    explored_nodes=0,
                    search_depth=0,
                    confidence=1.0,
                    reasoning_trace=["EMERGENCY BYPASS TRIGGERED: Critical physiological failure."],
                    branches_considered=[]
                )

        from scrubin.perf.budgets import PerformanceBudgets
        budgets = PerformanceBudgets()

        root = SearchNode(state=root_state)

        start_time = time.time()
        nodes_explored = 1
        rollout_count = 0

        if self.config.deterministic:
            random.seed(f"{seed}-{root_state.world.tick}")

        for iteration in range(self.config.iterations):
            wall_ms = (time.time() - start_time) * 1000
            budget_violation = budgets.check_mcts_wall_time(wall_ms)
            if budget_violation:
                break

            budget_violation = budgets.check_mcts_nodes(nodes_explored)
            if budget_violation:
                break

            if wall_ms > self.config.max_wall_time_ms:
                break

            if nodes_explored >= self.config.max_nodes:
                break

            node = self._select(root)
            if node.state.depth < self.config.max_depth:
                node = self._expand(node)
                nodes_explored += len(node.children) if node.children else 1

            utility = self._rollout(node.state)
            rollout_count += 1
            self._backpropagate(node, utility)

            budget_violation = budgets.check_rollouts(rollout_count)
            if budget_violation:
                break

        if not root.children:
            return None

        best_child = max(root.children, key=lambda c: c.visits)

        from scrubin.decision.explain import TraceGenerator
        expected_util = best_child.value / best_child.visits if best_child.visits > 0 else 0
        trace = TraceGenerator.generate_trace(
            best_child.action,
            root_state.world,
            best_child.state.world,
            self.utility_function.evaluate(root_state.world),
            expected_util
        )

        return PlanningResult(
            selected_action=best_child.action if best_child.action else "wait",
            expected_utility=expected_util,
            projected_mortality=best_child.state.world.mortality_risk,
            projected_sofa=best_child.state.world.sofa_score,
            explored_nodes=nodes_explored,
            search_depth=self.config.max_depth,
            confidence=float(best_child.visits) / float(self.config.iterations) if self.config.iterations > 0 else 0.0,
            reasoning_trace=trace.reasons,
            branches_considered=[]
        )

    def _select(self, node: SearchNode) -> SearchNode:
        while node.children:
            node = max(node.children, key=lambda c: c.uct(self.config.exploration_constant))
        return node

    def _expand(self, node: SearchNode) -> SearchNode:
        # Hierarchical Expansion: 
        # If node hasn't selected a category yet, expand categories.
        # If node has a category but no specific action, expand specific actions.
        if not hasattr(node, "category") or not node.category:
            categories = self._get_available_actions(node.state)
            for cat in categories:
                # We create intermediate category nodes
                child = SearchNode(state=node.state.clone(), parent=node)
                object.__setattr__(child, "category", cat)
                node.children.append(child)
            return random.choice(node.children) if node.children else node
            
        else:
            # We are in a category node, expand into actual actions
            actions = self._get_available_actions(node.state, category=node.category)
            for action in actions:
                new_state = self._apply_action(node.state, action)
                child = SearchNode(state=new_state, parent=node, action=action)
                node.children.append(child)
                
            return random.choice(node.children) if node.children else node

    def _rollout(self, state: PlanningState) -> float:
        current_state = state.clone()
        from scrubin.decision.policy import RolloutPolicy

        while current_state.depth < self.config.rollout_depth:
            hierarchy = self._get_action_hierarchy(current_state)
            flat_actions = []
            for acts in hierarchy.values():
                flat_actions.extend(acts)
            chosen_action = RolloutPolicy.select_action(current_state.world, flat_actions)
            current_state = self._apply_action(current_state, chosen_action)

            if self.invariant_validator is not None:
                violations = self.invariant_validator.validate_soft(current_state.world)
                if any(v.severity == "fatal" for v in violations):
                    return float("-inf")

        base_utility = self.utility_function.evaluate(current_state.world)
        return base_utility * (self.config.gamma ** current_state.depth)

    def _backpropagate(self, node: SearchNode, utility: float):
        while node is not None:
            node.visits += 1
            node.value += utility
            node = node.parent
