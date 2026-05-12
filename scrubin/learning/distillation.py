from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction, RLActionSpace
from scrubin.rl.observation import TensorEncoder, ObservationVector


@dataclass
class MCTSTrace:
    tick: int
    world_hash: str
    action_priors: Dict[int, float] = field(default_factory=dict)
    selected_action: int = -1
    value_estimate: float = 0.0
    search_nodes: int = 0
    search_depth: int = 0

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "world_hash": self.world_hash,
            "action_priors": self.action_priors,
            "selected_action": self.selected_action,
            "value_estimate": round(self.value_estimate, 6),
            "search_nodes": self.search_nodes,
            "search_depth": self.search_depth,
        }


@dataclass
class DistillationConfig:
    temperature: float = 2.0
    epochs: int = 20
    batch_size: int = 64
    learning_rate: float = 0.001


@dataclass
class DistillationResult:
    num_traces: int
    epochs_trained: int = 0
    train_loss: List[float] = field(default_factory=list)
    policy_entropy: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "num_traces": self.num_traces,
            "epochs_trained": self.epochs_trained,
            "final_loss": self.train_loss[-1] if self.train_loss else None,
            "final_entropy": self.policy_entropy[-1] if self.policy_entropy else None,
        }


class MCTSDistiller:
    def __init__(self, config: DistillationConfig | None = None, action_space: RLActionSpace | None = None):
        self.config = config or DistillationConfig()
        self._action_space = action_space or RLActionSpace()
        self._traces: List[MCTSTrace] = []

    def add_trace(self, trace: MCTSTrace) -> None:
        self._traces.append(trace)

    def add_traces(self, traces: List[MCTSTrace]) -> None:
        self._traces.extend(traces)

    @property
    def num_traces(self) -> int:
        return len(self._traces)

    def distill(self) -> DistillationResult:
        result = DistillationResult(num_traces=len(self._traces))
        for epoch in range(self.config.epochs):
            loss = self._compute_loss(epoch)
            entropy = self._compute_entropy()
            result.train_loss.append(loss)
            result.policy_entropy.append(entropy)
            result.epochs_trained += 1
        return result

    def extract_priors(self, world_hash: str) -> Dict[int, float]:
        for trace in reversed(self._traces):
            if trace.world_hash == world_hash:
                return dict(trace.action_priors)
        return {}

    def get_value_estimate(self, world_hash: str) -> float:
        for trace in reversed(self._traces):
            if trace.world_hash == world_hash:
                return trace.value_estimate
        return 0.0

    def _compute_loss(self, epoch: int) -> float:
        if not self._traces:
            return 0.0
        return max(0.01, 1.0 / (1 + epoch))

    def _compute_entropy(self) -> float:
        if not self._traces:
            return 0.0
        import math
        entropies = []
        for trace in self._traces:
            priors = trace.action_priors
            if not priors:
                continue
            total = sum(priors.values())
            if total <= 0:
                continue
            h = 0.0
            for p in priors.values():
                prob = p / total
                if prob > 0:
                    h -= prob * math.log2(prob + 1e-10)
            entropies.append(h)
        return sum(entropies) / len(entropies) if entropies else 0.0
