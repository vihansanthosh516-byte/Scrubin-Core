from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.observation import TensorEncoder, ObservationVector


@dataclass
class Transition:
    observation: List[float]
    action: int
    reward: float
    next_observation: List[float]
    done: bool
    info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "observation": self.observation,
            "action": self.action,
            "reward": round(self.reward, 6),
            "next_observation": self.next_observation,
            "done": self.done,
        }


class ReplayBuffer:
    def __init__(self, capacity: int = 10000):
        self._capacity = capacity
        self._buffer: List[Transition] = []

    def add(self, transition: Transition) -> None:
        if len(self._buffer) >= self._capacity:
            self._buffer.pop(0)
        self._buffer.append(transition)

    def add_batch(self, transitions: List[Transition]) -> None:
        for t in transitions:
            self.add(t)

    def sample(self, n: int) -> List[Transition]:
        if n >= len(self._buffer):
            return list(self._buffer)
        step = len(self._buffer) // n
        return [self._buffer[i * step] for i in range(n)]

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def capacity(self) -> int:
        return self._capacity

    def is_full(self) -> bool:
        return len(self._buffer) >= self._capacity

    def clear(self) -> None:
        self._buffer.clear()

    def all_transitions(self) -> List[Transition]:
        return list(self._buffer)

    def to_dict_list(self) -> List[dict]:
        return [t.to_dict() for t in self._buffer]


class ExpertTransitionBuffer:
    def __init__(self, capacity: int = 50000):
        self._buffer = ReplayBuffer(capacity=capacity)
        self._encoder = TensorEncoder()

    def record(
        self,
        observation_before: ObservationVector,
        action: ClinicalAction,
        reward: float,
        observation_after: ObservationVector,
        done: bool,
        info: dict | None = None,
    ) -> Transition:
        t = Transition(
            observation=observation_before.to_list(),
            action=action.value,
            reward=reward,
            next_observation=observation_after.to_list(),
            done=done,
            info=info or {},
        )
        self._buffer.add(t)
        return t

    @property
    def size(self) -> int:
        return self._buffer.size

    def sample(self, n: int) -> List[Transition]:
        return self._buffer.sample(n)

    def all_transitions(self) -> List[Transition]:
        return self._buffer.all_transitions()

    def clear(self) -> None:
        self._buffer.clear()
