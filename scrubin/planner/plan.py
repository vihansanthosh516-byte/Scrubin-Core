"""Immutable deterministic planning data models for Long‑Horizon Planner.

All IDs and hashes are derived deterministically from the plan contents.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Tuple


def deterministic_plan_id(root_tick: int, horizon: int, steps: Tuple["PlanStep", ...], total_score: float, confidence: float) -> str:
    """Deterministic identifier for a ``Plan``.

    The ID is ``plan-`` plus the first 12 hex characters of a SHA‑256 hash over a
    canonical JSON representation of the supplied fields.
    """
    # Convert steps to a serialisable form (list of dicts)
    steps_repr = [
        {
            "tick": s.tick,
            "action_id": s.action_id,
            "action_name": s.action_name,
            "expected_reward": s.expected_reward,
        }
        for s in steps
    ]
    canonical = json.dumps(
        {
            "root_tick": root_tick,
            "horizon": horizon,
            "steps": steps_repr,
            "total_score": total_score,
            "confidence": confidence,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"plan-{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def deterministic_plan_hash(plan: "Plan") -> str:
    """Deterministic replay hash for a fully populated ``Plan``.
    """
    data = {
        "id": plan.id,
        "root_tick": plan.root_tick,
        "horizon": plan.horizon,
        "steps": [
            {
                "tick": s.tick,
                "action_id": s.action_id,
                "action_name": s.action_name,
                "expected_reward": s.expected_reward,
                "replay_hash": s.replay_hash,
            }
            for s in plan.steps
        ],
        "total_score": plan.total_score,
        "confidence": plan.confidence,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class PlanStep:
    """Immutable step within a Long‑Horizon plan.

    ``expected_reward`` is a deterministic score component (0.0‑1.0).
    """
    tick: int
    action_id: str
    action_name: str
    expected_reward: float
    replay_hash: str = ""

    @staticmethod
    def create(tick: int, action_id: str, action_name: str, expected_reward: float) -> "PlanStep":
        placeholder = PlanStep(tick=tick, action_id=action_id, action_name=action_name, expected_reward=expected_reward, replay_hash="")
        return replace(placeholder, replay_hash=deterministic_plan_step_hash(placeholder))


def deterministic_plan_step_hash(step: PlanStep) -> str:
    """Deterministic hash for a ``PlanStep``.
    """
    data = {
        "tick": step.tick,
        "action_id": step.action_id,
        "action_name": step.action_name,
        "expected_reward": step.expected_reward,
    }
    json_repr = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(json_repr.encode()).hexdigest()


@dataclass(frozen=True)
class Plan:
    """Immutable deterministic plan consisting of a sequence of ``PlanStep`` objects.
    """
    id: str
    root_tick: int
    horizon: int
    steps: Tuple[PlanStep, ...]
    total_score: float
    confidence: float
    replay_hash: str

    @staticmethod
    def create(root_tick: int, horizon: int, steps: Tuple[PlanStep, ...], total_score: float, confidence: float) -> "Plan":
        plan_id = deterministic_plan_id(root_tick, horizon, steps, total_score, confidence)
        placeholder = Plan(
            id=plan_id,
            root_tick=root_tick,
            horizon=horizon,
            steps=steps,
            total_score=total_score,
            confidence=confidence,
            replay_hash="",
        )
        return replace(placeholder, replay_hash=deterministic_plan_hash(placeholder))
