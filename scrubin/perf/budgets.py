from dataclasses import dataclass
from typing import Optional


@dataclass
class PerformanceBudgets:
    MAX_TICK_TIME_MS: float = 100.0
    MAX_MCTS_NODES: int = 50_000
    MAX_ROLLOUTS: int = 10_000
    MAX_MCTS_WALL_TIME_MS: float = 1000.0
    MAX_VALIDATOR_TIME_MS: float = 20.0
    MAX_HASH_TIME_MS: float = 10.0
    MAX_SNAPSHOT_TIME_MS: float = 50.0

    def check_tick_budget(self, tick_duration_ms: float) -> Optional[str]:
        if tick_duration_ms > self.MAX_TICK_TIME_MS:
            return f"tick_duration={tick_duration_ms:.1f}ms > budget={self.MAX_TICK_TIME_MS}ms"
        return None

    def check_mcts_nodes(self, node_count: int) -> Optional[str]:
        if node_count > self.MAX_MCTS_NODES:
            return f"mcts_nodes={node_count} > budget={self.MAX_MCTS_NODES}"
        return None

    def check_rollouts(self, rollout_count: int) -> Optional[str]:
        if rollout_count > self.MAX_ROLLOUTS:
            return f"rollout_count={rollout_count} > budget={self.MAX_ROLLOUTS}"
        return None

    def check_mcts_wall_time(self, wall_time_ms: float) -> Optional[str]:
        if wall_time_ms > self.MAX_MCTS_WALL_TIME_MS:
            return f"mcts_wall_time={wall_time_ms:.1f}ms > budget={self.MAX_MCTS_WALL_TIME_MS}ms"
        return None

    def check_all(self, tick_duration_ms: float = 0, mcts_nodes: int = 0,
                  rollout_count: int = 0, mcts_wall_time_ms: float = 0) -> list[str]:
        violations = []
        v = self.check_tick_budget(tick_duration_ms)
        if v:
            violations.append(v)
        v = self.check_mcts_nodes(mcts_nodes)
        if v:
            violations.append(v)
        v = self.check_rollouts(rollout_count)
        if v:
            violations.append(v)
        v = self.check_mcts_wall_time(mcts_wall_time_ms)
        if v:
            violations.append(v)
        return violations
