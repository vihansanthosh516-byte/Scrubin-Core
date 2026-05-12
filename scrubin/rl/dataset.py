import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scrubin.rl.rollout import EpisodeTrajectory, RolloutResult


@dataclass
class TrajectoryRecord:
    episode_id: int
    seed: int
    total_reward: float
    survival: bool
    tick_count: int
    actions: List[int]
    rewards: List[float]
    mortality_curve: List[float]

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "seed": self.seed,
            "total_reward": round(self.total_reward, 6),
            "survival": self.survival,
            "tick_count": self.tick_count,
            "actions": self.actions,
            "rewards": [round(r, 6) for r in self.rewards],
            "mortality_curve": [round(m, 6) for m in self.mortality_curve],
        }

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class TrajectoryDataset:
    def __init__(self):
        self._records: List[TrajectoryRecord] = []

    def add_episode(self, trajectory: EpisodeTrajectory, episode_id: int | None = None) -> TrajectoryRecord:
        eid = episode_id if episode_id is not None else len(self._records)
        record = TrajectoryRecord(
            episode_id=eid,
            seed=trajectory.seed,
            total_reward=trajectory.total_reward,
            survival=trajectory.survival,
            tick_count=trajectory.tick_count,
            actions=list(trajectory.actions),
            rewards=list(trajectory.rewards),
            mortality_curve=list(trajectory.mortality_curve),
        )
        self._records.append(record)
        return record

    def add_rollout(self, result: RolloutResult, start_id: int = 0) -> List[TrajectoryRecord]:
        records = []
        for i, traj in enumerate(result.episodes):
            r = self.add_episode(traj, episode_id=start_id + i)
            records.append(r)
        return records

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def records(self) -> List[TrajectoryRecord]:
        return list(self._records)

    def export_jsonl(self, path: str) -> int:
        lines = [r.to_jsonl() for r in self._records]
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n" if lines else "")
        return len(lines)

    @classmethod
    def from_jsonl(cls, path: str) -> "TrajectoryDataset":
        ds = cls()
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                record = TrajectoryRecord(
                    episode_id=d["episode_id"],
                    seed=d["seed"],
                    total_reward=d["total_reward"],
                    survival=d["survival"],
                    tick_count=d["tick_count"],
                    actions=d["actions"],
                    rewards=d["rewards"],
                    mortality_curve=d["mortality_curve"],
                )
                ds._records.append(record)
        return ds

    def export_npz(self, path: str) -> int:
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy is required for NPZ export")
        arrays = {}
        if not self._records:
            arrays["episode_ids"] = np.array([], dtype=np.int32)
            arrays["seeds"] = np.array([], dtype=np.int32)
            arrays["rewards"] = np.array([], dtype=np.float64)
            arrays["survivals"] = np.array([], dtype=np.bool_)
        else:
            arrays["episode_ids"] = np.array([r.episode_id for r in self._records], dtype=np.int32)
            arrays["seeds"] = np.array([r.seed for r in self._records], dtype=np.int32)
            arrays["total_rewards"] = np.array([r.total_reward for r in self._records], dtype=np.float64)
            arrays["survivals"] = np.array([r.survival for r in self._records], dtype=np.bool_)
            arrays["tick_counts"] = np.array([r.tick_count for r in self._records], dtype=np.int32)
            max_len = max(len(r.actions) for r in self._records)
            actions_padded = np.full((len(self._records), max_len), -1, dtype=np.int32)
            rewards_padded = np.full((len(self._records), max_len), 0.0, dtype=np.float64)
            mortality_padded = np.full((len(self._records), max_len), -1.0, dtype=np.float64)
            for i, r in enumerate(self._records):
                for j, (a, rw, m) in enumerate(zip(r.actions, r.rewards, r.mortality_curve)):
                    actions_padded[i, j] = a
                    rewards_padded[i, j] = rw
                    mortality_padded[i, j] = m
            arrays["actions"] = actions_padded
            arrays["step_rewards"] = rewards_padded
            arrays["mortality_curves"] = mortality_padded
            arrays["max_episode_len"] = np.array([max_len], dtype=np.int32)
        np.savez(path, **arrays)
        return len(self._records)

    def summary(self) -> dict:
        if not self._records:
            return {"size": 0}
        rewards = [r.total_reward for r in self._records]
        survivals = [1 if r.survival else 0 for r in self._records]
        ticks = [r.tick_count for r in self._records]
        return {
            "size": len(self._records),
            "mean_reward": round(sum(rewards) / len(rewards), 6),
            "mean_survival_rate": round(sum(survivals) / len(survivals), 6),
            "mean_tick_count": round(sum(ticks) / len(ticks), 2),
            "max_reward": round(max(rewards), 6),
            "min_reward": round(min(rewards), 6),
        }
