from __future__ import annotations

"""Result of executing a :class:`DecisionNode`.

The result bundles the updated immutable ``WorldState`` together with any
educational feedback, generated timeline events, score deltas and a list of
unlocked options that become available after the decision.
"""

from dataclasses import dataclass, field
from typing import List, Any

from scrubin.world.state import WorldState
from scrubin.engine.decision_node import EducationalFeedback, HiddenEffect


@dataclass(frozen=True)
class DecisionResult:
    world: WorldState
    feedback: EducationalFeedback | None = None
    events: List[Any] = field(default_factory=list)  # TimelineEvent or similar
    score_delta: float = 0.0
    triggered_complications: List[HiddenEffect] = field(default_factory=list)
    unlocked_options: List[str] = field(default_factory=list)
