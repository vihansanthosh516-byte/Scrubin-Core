import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.reward import RewardConfig
from scrubin.world.model import SimulationWorld


@dataclass
class ScenarioConfig:
    scenario_id: str
    description: str
    difficulty: float
    max_ticks: int = 50
    seed_offset: int = 0
    reward_config: RewardConfig | None = None
    initial_mortality_bias: float = 0.0
    resource_constraint_level: float = 1.0

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "difficulty": round(self.difficulty, 2),
            "max_ticks": self.max_ticks,
            "seed_offset": self.seed_offset,
            "initial_mortality_bias": round(self.initial_mortality_bias, 6),
            "resource_constraint_level": round(self.resource_constraint_level, 6),
        }


@dataclass
class ScenarioBatch:
    batch_id: str
    configs: List[ScenarioConfig]
    total_scenarios: int

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "total_scenarios": self.total_scenarios,
            "configs": [c.to_dict() for c in self.configs],
        }


@dataclass
class GeneratedScenario:
    scenario_id: str
    seed: int
    difficulty: float
    world_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "difficulty": round(self.difficulty, 2),
            "metadata": self.metadata,
        }


def _difficulty_to_seed_range(difficulty: float) -> tuple[int, int]:
    base = int(difficulty * 10000)
    return (base, base + 1000)


CANONICAL_SCENARIO_CONFIGS: List[ScenarioConfig] = [
    ScenarioConfig(
        scenario_id="easy_stable",
        description="Easy: stable vitals, no intervention needed",
        difficulty=0.1,
        max_ticks=30,
        seed_offset=0,
        initial_mortality_bias=0.0,
        resource_constraint_level=1.0,
    ),
    ScenarioConfig(
        scenario_id="moderate_resp",
        description="Moderate: respiratory distress",
        difficulty=0.35,
        max_ticks=50,
        seed_offset=1000,
        initial_mortality_bias=0.15,
        resource_constraint_level=0.8,
    ),
    ScenarioConfig(
        scenario_id="moderate_cardio",
        description="Moderate: cardiovascular instability",
        difficulty=0.4,
        max_ticks=50,
        seed_offset=2000,
        initial_mortality_bias=0.2,
        resource_constraint_level=0.8,
    ),
    ScenarioConfig(
        scenario_id="hard_sepsis",
        description="Hard: sepsis with multi-system involvement",
        difficulty=0.65,
        max_ticks=80,
        seed_offset=3000,
        initial_mortality_bias=0.35,
        resource_constraint_level=0.6,
    ),
    ScenarioConfig(
        scenario_id="hard_shock",
        description="Hard: hemorrhagic shock",
        difficulty=0.7,
        max_ticks=80,
        seed_offset=4000,
        initial_mortality_bias=0.4,
        resource_constraint_level=0.5,
    ),
    ScenarioConfig(
        scenario_id="critical_multi_organ",
        description="Critical: multi-organ failure",
        difficulty=0.85,
        max_ticks=100,
        seed_offset=5000,
        initial_mortality_bias=0.5,
        resource_constraint_level=0.4,
    ),
    ScenarioConfig(
        scenario_id="extreme_resource_limited",
        description="Extreme: resource-limited critical care",
        difficulty=1.0,
        max_ticks=200,
        seed_offset=6000,
        initial_mortality_bias=0.6,
        resource_constraint_level=0.2,
    ),
]


class ScenarioGenerator:
    def __init__(
        self,
        base_seed: int = 0,
        configs: List[ScenarioConfig] | None = None,
    ):
        self._base_seed = base_seed
        self._configs = configs or CANONICAL_SCENARIO_CONFIGS

    def generate(self, config: ScenarioConfig, count: int = 1) -> List[GeneratedScenario]:
        scenarios = []
        for i in range(count):
            seed = self._base_seed + config.seed_offset + i
            scenarios.append(GeneratedScenario(
                scenario_id=f"{config.scenario_id}_{i}",
                seed=seed,
                difficulty=config.difficulty,
                metadata={
                    "max_ticks": config.max_ticks,
                    "initial_mortality_bias": config.initial_mortality_bias,
                    "resource_constraint_level": config.resource_constraint_level,
                },
            ))
        return scenarios

    def generate_batch(self, count_per_config: int = 5) -> ScenarioBatch:
        all_configs = []
        for config in self._configs:
            scenarios = self.generate(config, count=count_per_config)
            all_configs.append(config)
        return ScenarioBatch(
            batch_id=f"batch_{self._base_seed}",
            configs=all_configs,
            total_scenarios=len(all_configs) * count_per_config,
        )

    def generate_curriculum_batch(
        self,
        num_levels: int = 5,
        scenarios_per_level: int = 3,
    ) -> List[ScenarioConfig]:
        configs = []
        for i in range(num_levels):
            difficulty = (i + 1) / num_levels
            config = ScenarioConfig(
                scenario_id=f"curriculum_level_{i + 1}",
                description=f"Curriculum level {i + 1} (difficulty={difficulty:.1f})",
                difficulty=difficulty,
                max_ticks=30 + i * 20,
                seed_offset=i * 2000,
                initial_mortality_bias=difficulty * 0.5,
                resource_constraint_level=1.0 - difficulty * 0.6,
            )
            configs.append(config)
        return configs

    def generate_adversarial(
        self,
        base_difficulty: float = 0.5,
        num_scenarios: int = 10,
        spread: float = 0.15,
    ) -> List[ScenarioConfig]:
        configs = []
        for i in range(num_scenarios):
            offset = (random.random() - 0.5) * 2 * spread
            difficulty = max(0.0, min(1.0, base_difficulty + offset))
            config = ScenarioConfig(
                scenario_id=f"adversarial_{i}",
                description=f"Adversarial scenario {i} (difficulty={difficulty:.2f})",
                difficulty=difficulty,
                max_ticks=int(50 + difficulty * 100),
                seed_offset=i * 500 + 20000,
                initial_mortality_bias=difficulty * 0.4,
                resource_constraint_level=max(0.2, 1.0 - difficulty * 0.7),
            )
            configs.append(config)
        return configs

    @property
    def configs(self) -> List[ScenarioConfig]:
        return list(self._configs)

    @property
    def num_configs(self) -> int:
        return len(self._configs)
