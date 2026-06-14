"""Cognitive DAG verification.

Ensures the deterministic cognition layers form a directed acyclic graph (DAG)
with no cycles, deterministic ordering, and every node reachable from the
initial ``Events`` node. The verification runs at startup; any violation raises
a ``RuntimeError``.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Set

# Define the deterministic cognition pipeline as a DAG.
# Keys are node names; values are the list of downstream nodes that directly consume
# the output of the key.
# The ordering mirrors the executive pipeline described in the Phase 5.0 spec.
COGNITIVE_DEPENDENCIES: Dict[str, List[str]] = {
    "Events": ["EpisodeMemory"],
    "EpisodeMemory": ["SemanticFacts"],
    "SemanticFacts": ["Beliefs"],
    "Beliefs": ["Reflections"],
    "Reflections": ["KnowledgeGraph"],
    "KnowledgeGraph": ["Counterfactuals"],
    "Counterfactuals": ["MetaPatterns"],
    "MetaPatterns": ["LongHorizonPlanning"],
    "LongHorizonPlanning": ["ExecutiveGoals"],
    "ExecutiveGoals": ["StrategyLearning"],
    "StrategyLearning": ["StrategySelection"],
    "StrategySelection": ["ExecutiveEvaluation"],
    "ExecutiveEvaluation": ["PolicyProfiles"],
    "PolicyProfiles": ["BiasPlanning"],
    "BiasPlanning": ["ExecutiveFeedback"],
    "ExecutiveFeedback": ["AdaptationProfiles"],
    "AdaptationProfiles": ["AdaptationBias"],
    "AdaptationBias": ["ExecutiveOptimization"],
    "ExecutiveOptimization": ["SelfImprovement"],
    "SelfImprovement": ["PolicyArbitration"],
    "PredictiveWorldModel": ["PlannerDecision"],
    "PolicyArbitration": ["PredictiveWorldModel"],
    # Terminal node – planner consumes the decision but does not feed back into cognition.
    "PlannerDecision": [],
}

# Derive the full set of nodes from the keys and values.
ALL_NODES: Set[str] = set(COGNITIVE_DEPENDENCIES.keys())
for downstream in COGNITIVE_DEPENDENCIES.values():
    ALL_NODES.update(downstream)

def _topological_sort() -> List[str]:
    """Return a deterministic topological ordering of the cognitive graph.

    Raises ``RuntimeError`` if a cycle is detected.
    """
    # Compute in‑degree for each node.
    indegree: Dict[str, int] = {node: 0 for node in ALL_NODES}
    for src, dsts in COGNITIVE_DEPENDENCIES.items():
        for dst in dsts:
            indegree[dst] = indegree.get(dst, 0) + 1
    # Queue of nodes with indegree 0 – deterministic order by sorting.
    zero_indeg = deque(sorted([n for n, deg in indegree.items() if deg == 0]))
    order: List[str] = []
    while zero_indeg:
        node = zero_indeg.popleft()
        order.append(node)
        for nxt in COGNITIVE_DEPENDENCIES.get(node, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                # Maintain deterministic order by inserting in sorted position.
                # Since ``zero_indeg`` is a deque, we can append then sort after each insertion.
                zero_indeg.append(nxt)
        # Keep the deque sorted after possible new entries.
        zero_indeg = deque(sorted(zero_indeg))
    if len(order) != len(ALL_NODES):
        missing = ALL_NODES - set(order)
        raise RuntimeError(f"Cognitive graph contains a cycle or unreachable nodes: {missing}")
    return order


def verify_cognitive_graph() -> None:
    """Validate the cognition DAG at application startup.

    * Ensures there are no cycles.
    * Guarantees every node is reachable from ``Events``.
    * Confirms deterministic ordering (the returned order is sorted
      wherever nondeterministic choices could arise).
    Raises ``RuntimeError`` if any check fails.
    """
    order = _topological_sort()
    # Verify reachability from the root node (Events).
    reachable: Set[str] = set()
    stack = ["Events"]
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        stack.extend(COGNITIVE_DEPENDENCIES.get(node, []))
    unreachable = ALL_NODES - reachable
    if unreachable:
        raise RuntimeError(f"Unreachable cognitive nodes detected: {unreachable}")
    # The topological order itself provides deterministic ordering guarantee.
    # No further action needed; if the function returns without error the graph is valid.
    return None
