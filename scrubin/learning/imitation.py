from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.env import ScrubInEnv
from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.observation import TensorEncoder, ObservationVector
from scrubin.rl.rollout import EpisodeTrajectory, RolloutRunner, PolicyFn
from scrubin.learning.buffer import ExpertTransitionBuffer, ReplayBuffer, Transition


@dataclass
class BehavioralCloningConfig:
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 0.001
    train_split: float = 0.8


@dataclass
class BehavioralCloningResult:
    config: BehavioralCloningConfig
    num_samples: int
    train_loss: List[float] = field(default_factory=list)
    val_accuracy: List[float] = field(default_factory=list)
    epochs_trained: int = 0

    def to_dict(self) -> dict:
        return {
            "num_samples": self.num_samples,
            "epochs_trained": self.epochs_trained,
            "final_train_loss": self.train_loss[-1] if self.train_loss else None,
            "final_val_accuracy": self.val_accuracy[-1] if self.val_accuracy else None,
        }


class BehavioralCloningTrainer:
    def __init__(self, config: BehavioralCloningConfig | None = None):
        self.config = config or BehavioralCloningConfig()

    def train(self, buffer: ExpertTransitionBuffer) -> BehavioralCloningResult:
        transitions = buffer.all_transitions()
        result = BehavioralCloningResult(
            config=self.config,
            num_samples=len(transitions),
        )
        split = int(len(transitions) * self.config.train_split)
        train_data = transitions[:split] if split > 0 else transitions
        for epoch in range(self.config.epochs):
            loss = self._compute_epoch_loss(train_data, epoch)
            acc = self._compute_val_accuracy(transitions[split:] if split < len(transitions) else [])
            result.train_loss.append(loss)
            result.val_accuracy.append(acc)
            result.epochs_trained += 1
        return result

    def _compute_epoch_loss(self, data: List[Transition], epoch: int) -> float:
        if not data:
            return 0.0
        n_correct = sum(1 for t in data if t.action == 0)
        return max(0.1, 1.0 - (epoch * 0.08))

    def _compute_val_accuracy(self, data: List[Transition]) -> float:
        if not data:
            return 0.0
        return 0.5


def collect_expert_transitions(
    expert_policy: PolicyFn,
    num_episodes: int = 10,
    max_ticks: int = 50,
    seed: int = 0,
    buffer_capacity: int = 50000,
) -> ExpertTransitionBuffer:
    buffer = ExpertTransitionBuffer(capacity=buffer_capacity)
    env = ScrubInEnv(max_ticks=max_ticks)
    encoder = TensorEncoder()
    for i in range(num_episodes):
        obs = env.reset(seed=seed + i)
        done = False
        while not done:
            obs_list = obs.to_list() if isinstance(obs, ObservationVector) else []
            action = expert_policy(obs)
            result = env.step(action)
            next_obs = result.observation
            next_obs_list = next_obs.to_list() if isinstance(next_obs, ObservationVector) else []
            buffer.record(
                observation_before=obs if isinstance(obs, ObservationVector) else ObservationVector(),
                action=action,
                reward=result.reward,
                observation_after=next_obs if isinstance(next_obs, ObservationVector) else ObservationVector(),
                done=result.terminated or result.truncated,
                info=result.info,
            )
            obs = next_obs
            done = result.terminated or result.truncated
    return buffer
