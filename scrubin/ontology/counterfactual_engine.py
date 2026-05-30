from __future__ import annotations

"""Deterministic counterfactual reasoning engine.

The engine compares an executed intent against a deterministic alternative.
In this simplified version we generate a placeholder ``CounterfactualResult``
and emit a ``counterfactual_generated`` event.
"""

from typing import List

from scrubin.world.state import WorldState, TimelineEvent
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CounterfactualResult:
    divergence_score: float = 0.0
    avoided_risk: float = 0.0
    induced_risk: float = 0.0
    # ``semantic_difference_map`` omitted for brevity – could be a dict.

    def with_divergence(self, score: float) -> "CounterfactualResult":
        return replace(self, divergence_score=score)

    def with_avoided_risk(self, risk: float) -> "CounterfactualResult":
        return replace(self, avoided_risk=risk)

    def with_induced_risk(self, risk: float) -> "CounterfactualResult":
        return replace(self, induced_risk=risk)


class CounterfactualEngine:
    """Generate deterministic counterfactual comparisons.

    The stub does not inspect actual intents – it merely produces a constant
    ``CounterfactualResult`` for demonstration purposes.
    """

    def __init__(self, rng) -> None:
        self.rng = rng

    def analyze(self, world: WorldState) -> WorldState:
        # Produce a deterministic result.
        result = CounterfactualResult(divergence_score=0.0, avoided_risk=0.0, induced_risk=0.0)
        # Store result in world via a placeholder attribute (if needed).
        # Emit event.
        ev = TimelineEvent(world.tick, "counterfactual_generated")
        new_world = world.append_timeline(ev)
        return new_world
