"""Simple in‑memory registry for all DecisionNode objects.

The simulation orchestrator (or any AI agent) can look up a node via its
hierarchical ID and then call ``node.execute(world, rng)``.
"""

from __future__ import annotations

from typing import Dict

from .decision_node import DecisionNode


class DecisionRegistry:
    _registry: Dict[str, DecisionNode] = {}
    _counts: Dict[str, int] = {}

    @classmethod
    def register(cls, node: DecisionNode) -> None:
        """Add a ``DecisionNode`` to the global registry.

        The method tracks registration counts to enable duplicate‑ID validation.
        """
        # Track how many times a particular ID has been registered.
        cls._counts[node.id] = cls._counts.get(node.id, 0) + 1
        # Overwrite the entry – intentional for test overrides.
        cls._registry[node.id] = node

    @classmethod
    def get(cls, node_id: str) -> DecisionNode:
        return cls._registry[node_id]

    @classmethod
    def all(cls) -> Dict[str, DecisionNode]:
        return dict(cls._registry)

    @classmethod
    def validate(cls) -> None:
        """Validate the registry for structural integrity.

        Checks performed:
        * Duplicate IDs (registered more than once).
        * Unlock targets that do not exist in the registry.
        * Namespace format – IDs must contain at least three ``.`` separators.
        * Cyclic unlock references.
        """
        errors: List[str] = []

        # 1. Duplicate IDs
        duplicates = [node_id for node_id, cnt in cls._counts.items() if cnt > 1]
        if duplicates:
            errors.append(f"Duplicate node IDs detected: {', '.join(duplicates)}")

        # 2. Missing unlock targets
        all_ids = set(cls._registry.keys())
        for node in cls._registry.values():
            # ``option_mutation`` may be missing if the node was created manually.
            unlocks = getattr(node, "option_mutation", None)
            if unlocks is not None:
                for target in unlocks.unlock_options:
                    if target not in all_ids:
                        errors.append(f"Node {node.id} unlocks unknown target {target}")

        # 3. Namespace validation (e.g., ``appendectomy.a1.assessment.evaluate_symptoms``)
        for node_id in all_ids:
            parts = node_id.split('.')
            if len(parts) < 4 or any(p == '' for p in parts):
                errors.append(f"Invalid namespace for node ID '{node_id}'")

        # 4. Cycle detection in unlock graph.
        # Build directed graph: edge from node -> unlocked node.
        graph: Dict[str, List[str]] = {nid: [] for nid in all_ids}
        for node in cls._registry.values():
            unlocks = getattr(node, "option_mutation", None)
            if unlocks:
                for tgt in unlocks.unlock_options:
                    if tgt in all_ids:
                        graph[node.id].append(tgt)
        # Depth‑first search for cycles.
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(v: str) -> bool:
            visited.add(v)
            rec_stack.add(v)
            for neigh in graph.get(v, []):
                if neigh not in visited:
                    if dfs(neigh):
                        return True
                elif neigh in rec_stack:
                    return True
            rec_stack.remove(v)
            return False

        for nid in all_ids:
            if nid not in visited:
                if dfs(nid):
                    errors.append(f"Cyclic unlock reference involving node {nid}")
                    break

        if errors:
            raise ValueError("DecisionRegistry validation failed:\n" + "\n".join(errors))

