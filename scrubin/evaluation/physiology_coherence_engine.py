"""PhysiologyCoherenceEngine – validates physiological consistency.
The implementation inspects the supplied snapshot (if any) and reports any
detected issues.  The logic is deliberately simple and deterministic.
"""

from __future__ import annotations

from typing import Any

from .models import PhysiologyCoherenceReport


class PhysiologyCoherenceEngine:
    @staticmethod
    def evaluate(physiology_snapshot: Any = None) -> PhysiologyCoherenceReport:
        """Return a report describing physiological coherence issues.

        Currently the engine only checks for a missing snapshot and, as a stub,
        verifies that an attribute named ``organs`` (if present) contains unique
        identifiers.  No randomness is involved.
        """
        issues = ()
        if physiology_snapshot is None:
            issues = ("missing_snapshot",)
        else:
            # Example deterministic check for duplicate organ identifiers.
            if hasattr(physiology_snapshot, "organs"):
                organs = getattr(physiology_snapshot, "organs")
                # Assume ``organs`` is an iterable of objects with ``id``.
                ids = []
                for o in organs:
                    try:
                        ids.append(getattr(o, "id"))
                    except Exception:
                        ids.append(str(o))
                if len(set(ids)) != len(ids):
                    issues = ("duplicate_organs",)
        return PhysiologyCoherenceReport(issues=issues)
