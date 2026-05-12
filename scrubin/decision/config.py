from dataclasses import dataclass

@dataclass
class PlannerConfig:
    enabled: bool = True

    max_depth: int = 5
    rollout_depth: int = 8
    iterations: int = 150
    max_wall_time_ms: int = 500
    max_nodes: int = 5000

    exploration_constant: float = 1.41
    gamma: float = 0.95

    emergency_bypass: bool = True
    fallback_to_greedy: bool = True
    deterministic: bool = True
