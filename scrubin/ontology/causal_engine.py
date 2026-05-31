"""Causal engine stub for deterministic predictions.

Provides a minimal implementation of the ``CausalEngine`` used by the
semantic prediction engine.  The ``trace_causal_chain`` method returns an
empty list, yielding no prediction events – sufficient for the deterministic
tests that focus on the new intent synthesis layer.
"""

from __future__ import annotations

class CausalEngine:
    """Stub causal engine – deterministic no‑op implementation."""
    def __init__(self) -> None:
        pass

    def trace_causal_chain(self, concept_id: str, depth: int = 3):
        """Return an empty causal chain.

        Args:
            concept_id: Identifier of the source concept.
            depth: Maximum depth to traverse (ignored).
        Returns:
            Empty list, indicating no downstream causal relationships.
        """
        return []
