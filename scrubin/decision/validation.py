from dataclasses import dataclass
from typing import Optional
from scrubin.decision.mcts import MonteCarloTreeSearch
from scrubin.decision.planning import PlanningState

@dataclass
class PlannerValidationReport:
    chosen_action: str
    chosen_utility: float
    best_hindsight_action: str
    best_hindsight_utility: float
    planner_regret: float
    search_stability: float
    nodes_explored: int
    
class PlannerValidator:
    """
    Validates MCTS planner quality through regret analysis and search stability scoring.
    """
    def __init__(self, planner: MonteCarloTreeSearch):
        self.planner = planner
        
    def validate_decision(self, state: PlanningState, seed: int = 42) -> PlannerValidationReport:
        # Run standard planner
        result = self.planner.search(state, seed=seed)
        if not result:
            return PlannerValidationReport("none", 0.0, "none", 0.0, 0.0, 0.0, 0)
            
        chosen_action = result.selected_action
        chosen_utility = result.expected_utility
        
        # Hindsight baseline: shallow exhaustive evaluation to find 'true' best single-step utility
        # (This is simplified; a true hindsight uses infinite depth / time)
        best_action = "wait"
        best_utility = -float('inf')
        
        actions = self.planner._get_available_actions(state)
        for action in actions:
            test_state = self.planner._apply_action(state, action)
            util = self.planner.utility_function.evaluate(test_state.world)
            if util > best_utility:
                best_utility = util
                best_action = action
                
        # Regret is the difference between the 'true' best utility and what the planner expected
        # (Assuming the planner's expected utility tracks with true utility)
        regret = max(0.0, best_utility - chosen_utility)
        
        # Stability: Run with different seed, check if same action is chosen
        result_b = self.planner.search(state, seed=seed + 1)
        stability = 1.0 if (result_b and result_b.selected_action == chosen_action) else 0.0
        
        return PlannerValidationReport(
            chosen_action=chosen_action,
            chosen_utility=chosen_utility,
            best_hindsight_action=best_action,
            best_hindsight_utility=best_utility,
            planner_regret=regret,
            search_stability=stability,
            nodes_explored=result.explored_nodes
        )
