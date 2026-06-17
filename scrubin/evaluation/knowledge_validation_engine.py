"""KnowledgeValidationEngine – checks for contradictions and invalid inferences.
The implementation is intentionally lightweight but fully deterministic.
"""

from __future__ import annotations

from typing import Any

from .models import KnowledgeConsistencyReport


class KnowledgeValidationEngine:
    @staticmethod
    def evaluate(knowledge_snapshot: Any = None) -> KnowledgeConsistencyReport:
        """Detect simple knowledge consistency problems.

        * If the snapshot is missing, report a ``missing_snapshot`` issue.
        * If the snapshot provides an attribute ``beliefs`` (iterable), duplicate
          belief identifiers are considered contradictions.
        """
        contradictions = ()
        if knowledge_snapshot is None:
            contradictions = ("missing_snapshot",)
        else:
            if hasattr(knowledge_snapshot, "beliefs"):
                beliefs = getattr(knowledge_snapshot, "beliefs")
                ids = []
                for b in beliefs:
                    try:
                        ids.append(getattr(b, "belief_id"))
                    except Exception:
                        ids.append(str(b))
                if len(set(ids)) != len(ids):
                    contradictions = ("duplicate_belief_ids",)
        return KnowledgeConsistencyReport(contradictions=contradictions)
