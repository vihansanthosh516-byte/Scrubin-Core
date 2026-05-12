import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from scrubin.rl.rollout import EpisodeTrajectory, PolicyFn, RolloutRunner
from scrubin.rl.reward import RewardConfig
from scrubin.learning.evaluation import PolicyEvaluator, EvaluationResult
from scrubin.learning.metrics import CompositeMetrics, compute_all_metrics
from scrubin.learning.regret import RegretAnalyzer, RegretSummary, PolicyComparison


@dataclass
class MatchResult:
    policy_a: str
    policy_b: str
    scenario_seed: int
    reward_a: float
    reward_b: float
    survival_a: bool
    survival_b: bool
    winner: str

    def to_dict(self) -> dict:
        return {
            "policy_a": self.policy_a,
            "policy_b": self.policy_b,
            "scenario_seed": self.scenario_seed,
            "reward_a": round(self.reward_a, 6),
            "reward_b": round(self.reward_b, 6),
            "survival_a": self.survival_a,
            "survival_b": self.survival_b,
            "winner": self.winner,
        }


@dataclass
class TournamentStandings:
    policy_id: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_reward: float = 0.0
    mean_reward: float = 0.0
    win_rate: float = 0.0
    num_matches: int = 0

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "total_reward": round(self.total_reward, 6),
            "mean_reward": round(self.mean_reward, 6),
            "win_rate": round(self.win_rate, 6),
            "num_matches": self.num_matches,
        }


@dataclass
class TournamentResult:
    tournament_id: str
    num_policies: int
    num_rounds: int
    matches: List[MatchResult]
    standings: Dict[str, TournamentStandings]
    champion: str
    comparisons: List[PolicyComparison] = field(default_factory=list)

    @property
    def ranking(self) -> List[str]:
        return sorted(
            self.standings.keys(),
            key=lambda k: self.standings[k].win_rate,
            reverse=True,
        )

    def to_dict(self) -> dict:
        return {
            "tournament_id": self.tournament_id,
            "num_policies": self.num_policies,
            "num_rounds": self.num_rounds,
            "num_matches": len(self.matches),
            "champion": self.champion,
            "standings": {k: v.to_dict() for k, v in self.standings.items()},
            "comparisons": [c.to_dict() for c in self.comparisons],
        }


@dataclass
class StatisticalComparison:
    policy_a: str
    policy_b: str
    mean_delta: float
    p_value: float
    significant: bool
    confidence: float = 0.95
    effect_size: float = 0.0

    def to_dict(self) -> dict:
        return {
            "policy_a": self.policy_a,
            "policy_b": self.policy_b,
            "mean_delta": round(self.mean_delta, 6),
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "confidence": self.confidence,
            "effect_size": round(self.effect_size, 6),
        }


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(var)


class TournamentRunner:
    def __init__(
        self,
        num_rounds: int = 5,
        max_ticks: int = 50,
        base_seed: int = 0,
    ):
        self._num_rounds = num_rounds
        self._max_ticks = max_ticks
        self._base_seed = base_seed
        self._runner = RolloutRunner(max_ticks=max_ticks)
        self._regret_analyzer = RegretAnalyzer(
            num_episodes=num_rounds,
            max_ticks=max_ticks,
            base_seed=base_seed,
        )

    def run_tournament(
        self,
        policies: Dict[str, PolicyFn],
        tournament_id: str = "tournament",
    ) -> TournamentResult:
        policy_ids = list(policies.keys())
        matches: List[MatchResult] = []
        standings: Dict[str, TournamentStandings] = {
            pid: TournamentStandings(policy_id=pid) for pid in policy_ids
        }
        reward_history: Dict[str, List[float]] = {pid: [] for pid in policy_ids}
        for i, pid_a in enumerate(policy_ids):
            for j, pid_b in enumerate(policy_ids):
                if i >= j:
                    continue
                for round_num in range(self._num_rounds):
                    seed = self._base_seed + round_num * 1000 + i * 100 + j
                    result_a = self._runner.run_episode(policies[pid_a], seed=seed, max_steps=self._max_ticks)
                    result_b = self._runner.run_episode(policies[pid_b], seed=seed, max_steps=self._max_ticks)
                    if result_a.total_reward > result_b.total_reward:
                        winner = pid_a
                    elif result_b.total_reward > result_a.total_reward:
                        winner = pid_b
                    else:
                        winner = "draw"
                    matches.append(MatchResult(
                        policy_a=pid_a,
                        policy_b=pid_b,
                        scenario_seed=seed,
                        reward_a=result_a.total_reward,
                        reward_b=result_b.total_reward,
                        survival_a=result_a.survival,
                        survival_b=result_b.survival,
                        winner=winner,
                    ))
                    standings[pid_a].num_matches += 1
                    standings[pid_b].num_matches += 1
                    standings[pid_a].total_reward += result_a.total_reward
                    standings[pid_b].total_reward += result_b.total_reward
                    reward_history[pid_a].append(result_a.total_reward)
                    reward_history[pid_b].append(result_b.total_reward)
                    if winner == pid_a:
                        standings[pid_a].wins += 1
                        standings[pid_b].losses += 1
                    elif winner == pid_b:
                        standings[pid_b].wins += 1
                        standings[pid_a].losses += 1
                    else:
                        standings[pid_a].draws += 1
                        standings[pid_b].draws += 1
        for pid in policy_ids:
            s = standings[pid]
            s.mean_reward = s.total_reward / s.num_matches if s.num_matches else 0.0
            s.win_rate = s.wins / s.num_matches if s.num_matches else 0.0
        comparisons = []
        for i, pid_a in enumerate(policy_ids):
            for j, pid_b in enumerate(policy_ids):
                if i >= j:
                    continue
                regret = self._regret_analyzer.simple_regret(
                    reward_history[pid_a],
                    reward_history[pid_b],
                )
                regret.policy_id = pid_a
                regret.baseline_id = pid_b
                mean_a = _mean(reward_history[pid_a])
                mean_b = _mean(reward_history[pid_b])
                comparisons.append(PolicyComparison(
                    policy_a=pid_a,
                    policy_b=pid_b,
                    reward_delta=round(mean_a - mean_b, 6),
                    survival_delta=0.0,
                    composite_delta=0.0,
                    regret_summary=regret,
                ))
        champion = max(standings.keys(), key=lambda k: standings[k].win_rate)
        return TournamentResult(
            tournament_id=tournament_id,
            num_policies=len(policy_ids),
            num_rounds=self._num_rounds,
            matches=matches,
            standings=standings,
            champion=champion,
            comparisons=comparisons,
        )


class StatisticalComparator:
    def __init__(self, confidence: float = 0.95):
        self._confidence = confidence
        self._z_score = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)

    def compare(
        self,
        rewards_a: List[float],
        rewards_b: List[float],
        policy_a: str = "policy_a",
        policy_b: str = "policy_b",
    ) -> StatisticalComparison:
        n_a = len(rewards_a)
        n_b = len(rewards_b)
        if n_a == 0 or n_b == 0:
            return StatisticalComparison(
                policy_a=policy_a,
                policy_b=policy_b,
                mean_delta=0.0,
                p_value=1.0,
                significant=False,
                confidence=self._confidence,
            )
        mean_a = _mean(rewards_a)
        mean_b = _mean(rewards_b)
        std_a = _std(rewards_a)
        std_b = _std(rewards_b)
        mean_delta = mean_a - mean_b
        se = math.sqrt((std_a ** 2 / n_a) + (std_b ** 2 / n_b)) if n_a > 0 and n_b > 0 else 1.0
        if se > 0:
            z = abs(mean_delta) / se
            p_value = 2.0 * (1.0 - self._normal_cdf(z))
        else:
            p_value = 0.0 if abs(mean_delta) > 1e-10 else 1.0
        pooled_std = math.sqrt(((n_a - 1) * std_a ** 2 + (n_b - 1) * std_b ** 2) / max(1, n_a + n_b - 2)) if (n_a + n_b) > 2 else 1.0
        effect_size = mean_delta / pooled_std if pooled_std > 0 else 0.0
        significant = p_value < (1.0 - self._confidence)
        return StatisticalComparison(
            policy_a=policy_a,
            policy_b=policy_b,
            mean_delta=round(mean_delta, 6),
            p_value=round(p_value, 6),
            significant=significant,
            confidence=self._confidence,
            effect_size=round(effect_size, 6),
        )

    @staticmethod
    def _normal_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def pairwise_compare(
        self,
        policy_rewards: Dict[str, List[float]],
    ) -> List[StatisticalComparison]:
        ids = list(policy_rewards.keys())
        results = []
        for i, id_a in enumerate(ids):
            for j, id_b in enumerate(ids):
                if i >= j:
                    continue
                comp = self.compare(
                    policy_rewards[id_a],
                    policy_rewards[id_b],
                    policy_a=id_a,
                    policy_b=id_b,
                )
                results.append(comp)
        return results
