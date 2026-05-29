"""Deterministic multi‑agent runtime engine.

Updates each operative actor each tick, handling cognitive load, fatigue,
awareness, task queue execution, and communication latency. Emits timeline
events when thresholds are crossed.
"""

from __future__ import annotations

from typing import List, Tuple

from scrubin.world.state import WorldState, TimelineEvent
from scrubin.agents.state import OperativeActor


class MultiAgentRuntimeEngine:
    """Deterministic runtime for operative team actors.

    Pure – returns a new ``WorldState`` with updated actors and events.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def _update_actor(self, actor: OperativeActor, tick: int) -> OperativeActor:
        """Deterministically update a single actor.

        * Cognitive load grows with pending tasks.
        * Fatigue accumulates with load.
        * Situational awareness degrades with fatigue.
        * Response latency rises when load high and decays otherwise.
        * The first queued task is considered completed each tick.
        """
        # 1. Cognitive load increase
        load = min(1.0, actor.cognitive_load + 0.02 * len(actor.task_queue))
        # 2. Fatigue accumulation
        fatigue = min(1.0, actor.fatigue + 0.001 + 0.005 * actor.cognitive_load)
        # 3. Awareness degradation
        awareness = max(0.0, actor.situational_awareness - 0.01 * actor.fatigue)
        # 4. Latency adjustment
        latency = actor.response_latency
        if load > 0.7:
            latency = min(5, latency + 1)
        else:
            latency = max(0, latency - 1)
        # 5. Task queue – deterministic completion of first task
        queue = actor.task_queue
        if queue:
            queue = queue[1:]
        # Construct updated actor
        return (
            actor.with_cognitive_load(load)
            .with_fatigue(fatigue)
            .with_situational_awareness(awareness)
            .with_response_latency(latency)
            .with_task_queue(queue)
        )

    def evolve(self, world: WorldState) -> WorldState:
        """Evolve all actors for a simulation tick.

        Returns a new ``WorldState`` with updated actors and any generated
        timeline events.
        """
        new_actors: List[OperativeActor] = []
        events: List[TimelineEvent] = []
        for actor in world.actors:
            upd = self._update_actor(actor, world.tick)
            if upd.cognitive_load > 0.8:
                events.append(TimelineEvent(world.tick, f"communication_breakdown:{actor.role}"))
            if upd.fatigue > 0.9:
                events.append(TimelineEvent(world.tick, f"situational_awareness_loss:{actor.role}"))
            new_actors.append(upd)
        new_world = world.with_actors(tuple(new_actors))
        for ev in events:
            new_world = new_world.append_timeline(ev)
        return new_world
