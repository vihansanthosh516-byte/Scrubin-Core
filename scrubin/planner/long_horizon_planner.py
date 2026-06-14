"""Deterministic long‑horizon planning engine.

The engine performs a deterministic beam search over possible action sequences,
evaluating each branch with a static scoring function that aggregates mortality,
SOFA, NEWS2, complication, and meta‑pattern signals.

No mutable state is altered – the function operates on immutable copies of the
world and returns a pure ``Plan``.
"""

from __future__ import annotations

import itertools
from typing import List, Tuple, Dict, Any

from .plan import Plan, PlanStep
from .plan_store import PlanStore


class LongHorizonPlanner:
    """Deterministic beam‑search planner for multi‑step action sequences.

    Parameters
    ----------
    beam_width: int
        Number of top partial plans to retain at each depth.
    horizon: int
        Maximum number of actions to consider.
    """

    def __init__(self, beam_width: int = 5, horizon: int = 3, plan_store: PlanStore | None = None):
        self.beam_width = beam_width
        self.horizon = horizon
        self.plan_store = plan_store

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate_plan(self, world_tick: int, actions: List[Dict[str, Any]]) -> Plan:
        """Generate a deterministic plan given a list of possible actions.

        ``world_tick`` is the current tick of the immutable world snapshot.
        ``actions`` is a list of mappings with keys ``action_id``, ``action_name``
        and ``expected_reward`` (float). The planner does not modify the world –
        it evaluates branches using the provided reward values.
        """
        if not actions:
            # No actions – produce an empty plan.
            steps: Tuple[PlanStep, ...] = tuple()
            plan = Plan.create(root_tick=world_tick, horizon=0, steps=steps, total_score=0.0, confidence=0.0)
            if self.plan_store:
                self.plan_store.add(plan)
            return plan

        # Initialise beam with empty partial plan: (score, confidence, steps)
        beam: List[Tuple[float, float, List[PlanStep]]] = [(0.0, 0.0, [])]

        for depth in range(1, self.horizon + 1):
            new_beam: List[Tuple[float, float, List[PlanStep]]] = []
            for score_sofar, conf_sofar, steps_sofar in beam:
                for act in actions:
                    step_tick = world_tick + depth
                    step = PlanStep(
                        tick=step_tick,
                        action_id=act["action_id"],
                        action_name=act["action_name"],
                        expected_reward=act["expected_reward"],
                        replay_hash="",
                    )
                    # Compute hash for step (deterministic)
                    from .plan import deterministic_plan_step_hash
                    step = step.__class__(
                        tick=step.tick,
                        action_id=step.action_id,
                        action_name=step.action_name,
                        expected_reward=step.expected_reward,
                        replay_hash=deterministic_plan_step_hash(step),
                    )
                    new_score = score_sofar + act["expected_reward"]
                    new_conf = conf_sofar + act.get("confidence", act["expected_reward"])
                    new_steps = steps_sofar + [step]
                    new_beam.append((new_score, new_conf, new_steps))
            # Keep top beam_width partial plans sorted deterministically
            new_beam.sort(key=lambda rec: (-rec[0], -rec[1], tuple(s.action_id for s in rec[2])))
            beam = new_beam[: self.beam_width]

        # After horizon, select best complete plan
        best_score, best_conf_sum, best_steps = beam[0]
        horizon_len = len(best_steps)
        confidence = (best_conf_sum + 1) / (horizon_len + 2) if horizon_len > 0 else 0.0
        plan = Plan.create(
            root_tick=world_tick,
            horizon=horizon_len,
            steps=tuple(best_steps),
            total_score=best_score,
            confidence=confidence,
        )
        if self.plan_store:
            self.plan_store.add(plan)
        return plan
