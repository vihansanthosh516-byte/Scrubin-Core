from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.ledger import EventLedger
from scrubin.rl.action_space import ClinicalAction, RLActionSpace
from scrubin.rl.observation import DictEncoder, TensorEncoder, ObservationVector
from scrubin.rl.reward import RewardComponents, RewardConfig, RewardShaper
from scrubin.world.model import SimulationWorld
from scrubin.replay.hash import world_hash


@dataclass
class EnvStepResult:
    observation: Any
    reward: float
    terminated: bool
    truncated: bool
    info: dict

    def to_dict(self) -> dict:
        return {
            "reward": self.reward,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "info": self.info,
        }


@dataclass
class EnvInfo:
    tick: int = 0
    world_hash: str = ""
    reward_components: Optional[RewardComponents] = None
    action_executed: bool = False
    action_reason: str = ""


class ScrubInEnv:
    def __init__(
        self,
        max_ticks: int = 200,
        snapshot_interval: int = 50,
        reward_config: RewardConfig | None = None,
        action_space: RLActionSpace | None = None,
        encoder: str = "tensor",
    ):
        self._max_ticks = max_ticks
        self._snapshot_interval = snapshot_interval
        self._reward_shaper = RewardShaper(config=reward_config)
        self._action_space = action_space or RLActionSpace()
        self._encoder_name = encoder
        self._dict_encoder = DictEncoder()
        self._tensor_encoder = TensorEncoder()
        self._orchestrator: Optional[Orchestrator] = None
        self._world_before: Optional[SimulationWorld] = None
        self._seed: Optional[int] = None
        self._done = False
        self._total_reward = 0.0
        self._step_count = 0

    @property
    def action_space(self) -> RLActionSpace:
        return self._action_space

    @property
    def orchestrator(self) -> Optional[Orchestrator]:
        return self._orchestrator

    def reset(self, seed: int | None = None) -> Any:
        self._seed = seed
        self._done = False
        self._total_reward = 0.0
        self._step_count = 0
        self._orchestrator = Orchestrator(
            seed=seed or 0,
            snapshot_interval=self._snapshot_interval,
        )
        self._orchestrator.setup()
        self._world_before = None
        return self._observe()

    def step(self, action: ClinicalAction) -> EnvStepResult:
        if self._done or self._orchestrator is None:
            return EnvStepResult(
                observation=self._observe(),
                reward=0.0,
                terminated=True,
                truncated=False,
                info={"error": "environment is done or not initialized"},
            )

        world_before = self._copy_world()

        target = ""
        for k, v in world_before.hidden_state.items():
            target = k
            break

        intent = self._action_space.to_intent(
            action, target=target, source="rl_policy", reasoning=f"RL action {action.name}"
        )

        exec_result = self._orchestrator.authority.execute(intent)
        action_executed = exec_result.executed
        action_reason = exec_result.reason

        self._orchestrator.tick()
        self._step_count += 1

        world_after = self._orchestrator.world

        reward_components = self._reward_shaper.compute(
            world_before=world_before,
            world_after=world_after,
            action_taken=intent.name if action_executed else None,
            tick=self._orchestrator.tick_count,
        )
        reward = reward_components.total

        self._total_reward += reward
        self._world_before = world_before

        terminated = world_after.mortality_risk >= 1.0
        truncated = self._step_count >= self._max_ticks

        if terminated or truncated:
            self._done = True

        info = {
            "tick": self._orchestrator.tick_count,
            "world_hash": world_hash(world_after),
            "reward_components": reward_components.to_dict(),
            "action_executed": action_executed,
            "action_reason": action_reason,
            "total_reward": self._total_reward,
        }

        return EnvStepResult(
            observation=self._observe(),
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info=info,
        )

    def observe(self) -> Any:
        return self._observe()

    def _observe(self) -> Any:
        if self._orchestrator is None:
            return {} if self._encoder_name == "dict" else ObservationVector()
        world = self._orchestrator.world
        if self._encoder_name == "dict":
            return self._dict_encoder.encode(world)
        return self._tensor_encoder.encode(world)

    def _copy_world(self) -> SimulationWorld:
        # The world state is immutable; a deep copy is unnecessary for reward shaping.
        # Returning the reference directly avoids costly serialization/deserialization.
        if self._orchestrator is None:
            return SimulationWorld()
        return self._orchestrator.world

    @property
    def observation_dim(self) -> int:
        if self._encoder_name == "tensor":
            return self._tensor_encoder.dim
        return 0

    def get_world(self) -> Optional[SimulationWorld]:
        if self._orchestrator is not None:
            return self._orchestrator.world
        return None

    @property
    def total_reward(self) -> float:
        return self._total_reward

    @property
    def step_count(self) -> int:
        return self._step_count
