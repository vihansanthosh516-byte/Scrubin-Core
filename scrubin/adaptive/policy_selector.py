'''Deterministic policy selection for the adaptive planning engine.

The ``PolicySelector`` consumes a variety of inputs – learned policies, executive
goals, decisions, experience patterns, generalized rules, and the knowledge
graph – and produces an ordered tuple of ``PolicyCandidate`` objects.

Ordering rules (as required by the specification):
    1. Higher ``priority`` first.
    2. Higher ``confidence`` next.
    3. Lexical ``policy_id`` as a tie‑breaker.

All operations are deterministic: objects are inspected via attribute access or
dictionary keys, and the resulting candidates are sorted using a stable key.
''' 

from __future__ import annotations

from typing import Iterable, Tuple, Any, List

from .models import PolicyCandidate


class PolicySelector:
    """Select deterministic policy candidates.

    The public ``select`` method aggregates candidate information from the
    supplied iterables and returns a sorted ``tuple`` of ``PolicyCandidate``.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def _candidate_from_item(item: Any) -> PolicyCandidate:
        """Create a ``PolicyCandidate`` from a generic item.

        ``item`` may be a dataclass, a mapping, or any object with the expected
        attributes. Missing fields default to safe zero values.
        """
        # Attribute‑first, then dict‑lookup; fallback to ``str(item)`` for the id.
        policy_id = getattr(item, "policy_id", None) or (item.get("policy_id") if isinstance(item, dict) else str(item))
        priority = getattr(item, "priority", None) or (item.get("priority") if isinstance(item, dict) else 0)
        confidence = getattr(item, "confidence", None) or (item.get("confidence") if isinstance(item, dict) else 0.0)
        source = getattr(item, "__class__", type(item)).__name__
        return PolicyCandidate(policy_id=str(policy_id), priority=int(priority), confidence=float(confidence), source=source)

    def select(
        self,
        learned_policies: Iterable[Any] = (),
        executive_goals: Iterable[Any] = (),
        executive_decisions: Iterable[Any] = (),
        experience_patterns: Iterable[Any] = (),
        generalized_rules: Iterable[Any] = (),
        knowledge_graph: Any = None,
    ) -> Tuple[PolicyCandidate, ...]:
        """Deterministically select and order policy candidates.

        The function concatenates all sources, extracts a ``PolicyCandidate``
        for each entry, and sorts according to the specification.
        """
        all_sources: List[Iterable[Any]] = [
            learned_policies,
            executive_goals,
            executive_decisions,
            experience_patterns,
            generalized_rules,
        ]
        candidates: List[PolicyCandidate] = []
        for src in all_sources:
            for item in src:
                candidates.append(self._candidate_from_item(item))
        # Deterministic ordering – priority (desc), confidence (desc), lexical id.
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (-c.priority, -c.confidence, c.policy_id),
        )
        return tuple(sorted_candidates)
