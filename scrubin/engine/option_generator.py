"""Dynamic option generator for the deterministic procedural cognition engine.

The generator derives available options directly from the immutable ``WorldState``
using the unlock information stored on each ``DecisionNode``.  It no longer
relies on the legacy ``scrubin.decision.engine.DecisionEngine``.
"""

from __future__ import annotations

from typing import List

from scrubin.engine.decision_node import DecisionNode, OptionMutationRule
from scrubin.engine.decision_registry import DecisionRegistry
from scrubin.engine.decision_result import DecisionResult
from scrubin.world.state import WorldState, TimelineEvent


class DynamicOptionGenerator:
    """Generate decision options for a given ``WorldState``.

    The ``generate_options`` method examines the current ``cognitive`` state to
    determine which node IDs are available.  It returns a list of ``DecisionResult``
    objects that contain the minimal information required for UI presentation.
    """

    def __init__(self):
        # No internal engine – the generator works purely from the registry.
        pass

    def generate_options(self, world: WorldState) -> List[DecisionNode]:
        """Return ``DecisionNode`` objects that are currently unlocked.

        An option is unlocked if:
        * It has not been executed yet (not in ``world.cognitive.decisions``), and
        * It appears in the ``available_options`` list maintained by the
          ``cognitive`` state.  If ``available_options`` is empty, we fall back
          to any nodes whose unlock requirements are satisfied by the history.
        """
        executed = set(world.cognitive.decisions)
        available = set(world.cognitive.available_options)
        # If the cognitive state provides a concrete list, honour it.
        if available:
            return [DecisionRegistry.get(node_id) for node_id in available if node_id not in executed]

        # Otherwise, compute unlocks based on the history.
        unlocks: set[str] = set()
        for nid in executed:
            node = DecisionRegistry.get(nid)
            unlocks.update(node.option_mutation.unlock_options)
        # Filter out already executed nodes.
        candidates = [DecisionRegistry.get(node_id) for node_id in unlocks if node_id not in executed]
        return candidates


