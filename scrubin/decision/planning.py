from dataclasses import dataclass, field
from scrubin.world.model import SimulationWorld

@dataclass
class PlanningState:
    """
    Represents a specific deterministic state within the MCTS tree.
    """
    world: SimulationWorld
    depth: int = 0
    cumulative_utility: float = 0.0
    action_history: list[str] = field(default_factory=list)
    
    def clone(self) -> "PlanningState":
        import copy
        # We deepcopy the world state so rollouts don't pollute the actual simulation
        return PlanningState(
            world=copy.deepcopy(self.world),
            depth=self.depth,
            cumulative_utility=self.cumulative_utility,
            action_history=list(self.action_history)
        )
