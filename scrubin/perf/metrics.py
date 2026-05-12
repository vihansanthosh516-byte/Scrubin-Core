from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TickMetrics:
    tick: int = 0
    tick_duration_ms: float = 0.0
    evolve_duration_ms: float = 0.0
    planner_duration_ms: float = 0.0
    validator_duration_ms: float = 0.0


@dataclass
class MCTSMetrics:
    node_count: int = 0
    rollout_count: int = 0
    branch_factor: float = 0.0
    max_depth: int = 0
    average_utility: float = 0.0
    prune_rate: float = 0.0
    wall_time_ms: float = 0.0


@dataclass
class HospitalMetrics:
    patients_active: int = 0
    icu_utilization: float = 0.0
    queue_latency: float = 0.0
    resource_contention: float = 0.0


class PerformanceMetrics:
    def __init__(self, ledger=None):
        self._tick_metrics: List[TickMetrics] = []
        self._mcts_metrics: List[MCTSMetrics] = []
        self._hospital_metrics: List[HospitalMetrics] = []
        self._ledger = ledger
        self._budget_violations: List[str] = []

    def record_tick(self, metrics: TickMetrics):
        self._tick_metrics.append(metrics)

    def record_mcts(self, metrics: MCTSMetrics):
        self._mcts_metrics.append(metrics)
        if self._ledger is not None:
            self._ledger.log(
                "mcts_metrics",
                {
                    "node_count": metrics.node_count,
                    "rollout_count": metrics.rollout_count,
                    "branch_factor": round(metrics.branch_factor, 3),
                    "max_depth": metrics.max_depth,
                    "average_utility": round(metrics.average_utility, 6),
                    "prune_rate": round(metrics.prune_rate, 3),
                    "wall_time_ms": round(metrics.wall_time_ms, 2),
                },
                tick=0,
            )

    def record_hospital(self, metrics: HospitalMetrics):
        self._hospital_metrics.append(metrics)

    def record_budget_violation(self, violation: str):
        self._budget_violations.append(violation)
        if self._ledger is not None:
            self._ledger.log(
                "budget_violation",
                {"violation": violation},
                tick=0,
            )

    @property
    def tick_metrics(self) -> List[TickMetrics]:
        return list(self._tick_metrics)

    @property
    def mcts_metrics(self) -> List[MCTSMetrics]:
        return list(self._mcts_metrics)

    @property
    def hospital_metrics(self) -> List[HospitalMetrics]:
        return list(self._hospital_metrics)

    @property
    def budget_violations(self) -> List[str]:
        return list(self._budget_violations)

    def summary(self) -> dict:
        tick_durations = [t.tick_duration_ms for t in self._tick_metrics]
        return {
            "total_ticks": len(self._tick_metrics),
            "avg_tick_ms": sum(tick_durations) / len(tick_durations) if tick_durations else 0,
            "max_tick_ms": max(tick_durations) if tick_durations else 0,
            "total_mcts_searches": len(self._mcts_metrics),
            "total_budget_violations": len(self._budget_violations),
        }
