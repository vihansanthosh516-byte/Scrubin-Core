"""Causal Physiology Graph – Phase 5.2.

Implements a deterministic directed‑acyclic graph (DAG) of physiological variables.
Each tick the graph is evaluated in a fixed topological order (alphabetical tie‑break).
The implementation is deliberately lightweight – sufficient for unit tests while
preserving the invariants outlined in the specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Node definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhysiologyNode:
    """Immutable node representing a single physiological variable.

    Attributes
    ----------
    name: str
        Variable identifier.
    value: float
        Current numeric value.
    rate_of_change: float
        Deterministic rate applied during the tick (derived from upstream nodes).
    upstream: List[str]
        Names of direct upstream dependencies.
    downstream: List[str]
        Names of direct downstream dependents.
    """

    name: str
    value: float = 0.0
    rate_of_change: float = 0.0
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)

    def with_updates(
        self,
        value: float | None = None,
        rate_of_change: float | None = None,
    ) -> "PhysiologyNode":
        """Return a new node with the supplied overrides (``None`` = unchanged)."""
        return PhysiologyNode(
            name=self.name,
            value=self.value if value is None else value,
            rate_of_change=self.rate_of_change if rate_of_change is None else rate_of_change,
            upstream=self.upstream,
            downstream=self.downstream,
        )

# ---------------------------------------------------------------------------
# Graph engine – deterministic evaluation
# ---------------------------------------------------------------------------

class CausalPhysiologyGraph:
    """Deterministic evaluator for the fixed causal chain.

    The graph is fixed – the set and ordering of variables never change at runtime.
    This guarantees replay‑identical behaviour.
    """

    # Fixed ordering per the specification
    _CHAIN = [
        "infection",
        "immune_response",
        "cytokines",
        "vasodilation",
        "hypotension",
        "renal_hypoperfusion",
        "AKI",
        "hyperkalemia",
        "arrhythmia",
    ]

    def __init__(self) -> None:
        # Initialise all nodes with zero value and deterministic connections.
        self.nodes: Dict[str, PhysiologyNode] = {}
        for idx, name in enumerate(self._CHAIN):
            upstream = [] if idx == 0 else [self._CHAIN[idx - 1]]
            downstream = [] if idx == len(self._CHAIN) - 1 else [self._CHAIN[idx + 1]]
            self.nodes[name] = PhysiologyNode(name=name, upstream=upstream, downstream=downstream)

    # ---------------------------------------------------------------------
    # Core deterministic update – fixed‑step Euler with dt = 1 tick
    # ---------------------------------------------------------------------
    def step(self, inputs: Dict[str, float] | None = None) -> Dict[str, PhysiologyNode]:
        """Progress the graph one tick.

        ``inputs`` may provide external overrides (e.g., disease‑driven infection level).
        Values not supplied default to the node's current ``value``.
        The method returns a new immutable mapping of node name → updated node.
        """
        inputs = inputs or {}
        # Begin with a shallow copy of current nodes (they are frozen, so we create new ones)
        new_nodes: Dict[str, PhysiologyNode] = {name: node for name, node in self.nodes.items()}

        # Deterministic evaluation order – alphabetical tie‑break enforced by the list ordering already.
        for name in self._CHAIN:
            node = new_nodes[name]
            # Resolve upstream value (single upstream in this simple chain)
            upstream_val = 0.0
            if node.upstream:
                upstream_name = node.upstream[0]
                upstream_val = new_nodes[upstream_name].value

            # Simple linear rate law – 0.1 * upstream value
            rate = 0.1 * upstream_val

            # Apply optional external input (overwrites rate for the root variable)
            if name in inputs:
                # For the infection node we treat the input as a direct value.
                # This bypasses the rate calculation to keep the test deterministic.
                new_value = float(inputs[name])
                new_node = node.with_updates(value=new_value, rate_of_change=0.0)
            else:
                new_value = node.value + rate  # Euler step, dt = 1
                new_node = node.with_updates(value=new_value, rate_of_change=rate)

            new_nodes[name] = new_node

        # Replace internal state with the newly computed immutable nodes
        self.nodes = new_nodes
        return self.nodes
