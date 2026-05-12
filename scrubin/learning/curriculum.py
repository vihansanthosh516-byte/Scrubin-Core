from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import EpisodeTrajectory, PolicyFn, RolloutRunner
from scrubin.rl.reward import RewardConfig
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import CompositeMetrics, compute_all_metrics
from scrubin.learning.policy_registry import PolicyRegistry, PolicyMetadata


@dataclass
class CurriculumLevel:
    level_id: str
    difficulty: float
    max_ticks: int = 50
    description: str = ""
    reward_config: RewardConfig | None = None
    seed_range: tuple[int, int] = (0, 1000)
    graduation_threshold: float = 0.6
    num_episodes: int = 10

    def to_dict(self) -> dict:
        return {
            "level_id": self.level_id,
            "difficulty": round(self.difficulty, 2),
            "max_ticks": self.max_ticks,
            "description": self.description,
            "graduation_threshold": round(self.graduation_threshold, 6),
            "num_episodes": self.num_episodes,
        }


@dataclass
class CurriculumProgress:
    level_id: str
    attempts: int = 0
    best_score: float = 0.0
    mean_score: float = 0.0
    graduated: bool = False

    def to_dict(self) -> dict:
        return {
            "level_id": self.level_id,
            "attempts": self.attempts,
            "best_score": round(self.best_score, 6),
            "mean_score": round(self.mean_score, 6),
            "graduated": self.graduated,
        }


@dataclass
class CurriculumResult:
    total_levels: int
    levels_completed: int
    final_score: float
    progress: List[CurriculumProgress]
    policy_id: str = ""

    def to_dict(self) -> dict:
        return {
            "total_levels": self.total_levels,
            "levels_completed": self.levels_completed,
            "final_score": round(self.final_score, 6),
            "policy_id": self.policy_id,
            "progress": [p.to_dict() for p in self.progress],
        }


CANONICAL_CURRICULUM: List[CurriculumLevel] = [
    CurriculumLevel(
        level_id="basic_stable",
        difficulty=0.1,
        max_ticks=30,
        description="Stable patients requiring minimal intervention",
        graduation_threshold=0.8,
        num_episodes=5,
        seed_range=(0, 500),
    ),
    CurriculumLevel(
        level_id="moderate_instability",
        difficulty=0.3,
        max_ticks=50,
        description="Moderate vital sign instability",
        graduation_threshold=0.6,
        num_episodes=10,
        seed_range=(500, 1500),
    ),
    CurriculumLevel(
        level_id="acute_deterioration",
        difficulty=0.6,
        max_ticks=80,
        description="Acute deterioration requiring timely intervention",
        graduation_threshold=0.5,
        num_episodes=10,
        seed_range=(1500, 3000),
    ),
    CurriculumLevel(
        level_id="critical_multi_organ",
        difficulty=0.8,
        max_ticks=100,
        description="Critical multi-organ failure",
        graduation_threshold=0.4,
        num_episodes=15,
        seed_range=(3000, 5000),
    ),
    CurriculumLevel(
        level_id="extreme_stress",
        difficulty=1.0,
        max_ticks=200,
        description="Extreme stress test with resource constraints",
        graduation_threshold=0.3,
        num_episodes=20,
        seed_range=(5000, 10000),
    ),
]


class CurriculumTrainer:
    def __init__(
        self,
        curriculum: List[CurriculumLevel] | None = None,
        max_attempts_per_level: int = 5,
        base_seed: int = 0,
    ):
        self._curriculum = curriculum or CANONICAL_CURRICULUM
        self._max_attempts = max_attempts_per_level
        self._base_seed = base_seed
        self._progress: Dict[str, CurriculumProgress] = {}

    def evaluate_level(
        self,
        policy_fn: PolicyFn,
        level: CurriculumLevel,
        base_seed: int = 0,
    ) -> float:
        runner = RolloutRunner(max_ticks=level.max_ticks)
        result = runner.run_batch(
            policy=policy_fn,
            num_episodes=level.num_episodes,
            base_seed=base_seed,
        )
        metrics = compute_all_metrics(result.episodes)
        return metrics.composite_score

    def run_level(
        self,
        policy_fn: PolicyFn,
        level: CurriculumLevel,
        base_seed: int = 0,
    ) -> CurriculumProgress:
        progress = self._progress.get(level.level_id, CurriculumProgress(level_id=level.level_id))
        score = self.evaluate_level(policy_fn, level, base_seed)
        progress.attempts += 1
        progress.best_score = max(progress.best_score, score)
        if progress.attempts > 1:
            progress.mean_score = (progress.mean_score * (progress.attempts - 1) + score) / progress.attempts
        else:
            progress.mean_score = score
        if score >= level.graduation_threshold:
            progress.graduated = True
        self._progress[level.level_id] = progress
        return progress

    def run_curriculum(
        self,
        policy_fn: PolicyFn,
        policy_id: str = "",
    ) -> CurriculumResult:
        completed = 0
        for level in self._curriculum:
            seed = self._base_seed + level.seed_range[0]
            graduated = False
            for attempt in range(self._max_attempts):
                progress = self.run_level(policy_fn, level, base_seed=seed + attempt * 100)
                if progress.graduated:
                    graduated = True
                    break
            if graduated:
                completed += 1
            else:
                break
        final_score = 0.0
        progress_list = list(self._progress.values())
        if progress_list:
            final_score = max(p.best_score for p in progress_list)
        return CurriculumResult(
            total_levels=len(self._curriculum),
            levels_completed=completed,
            final_score=final_score,
            progress=progress_list,
            policy_id=policy_id,
        )

    @property
    def progress(self) -> Dict[str, CurriculumProgress]:
        return dict(self._progress)

    def reset(self) -> None:
        self._progress.clear()
