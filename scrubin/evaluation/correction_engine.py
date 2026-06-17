"""CorrectionEngine – produces a deterministic set of correction proposals.
The engine examines the issues reported by upstream engines and creates
immutable ``CorrectionProposal`` objects.  Proposals are sorted deterministically
by description and action to guarantee reproducibility.
"""

from __future__ import annotations

from typing import Iterable

from .models import CorrectionProposal, CorrectionSet


class CorrectionEngine:
    @staticmethod
    def generate(*reports) -> CorrectionSet:
        """Generate deterministic correction proposals from any number of reports.

        Each report that provides an ``issues`` or ``contradictions`` attribute is
        inspected, and a ``CorrectionProposal`` with action ``"address_issue"`` is
        created for every distinct issue string.  Duplicate proposals are
        de‑duplicated, and the final set is sorted by description and action.
        """
        raw: list[CorrectionProposal] = []
        for rpt in reports:
            # Determine the container of issue strings.
            if hasattr(rpt, "issues"):
                issues = getattr(rpt, "issues")
            elif hasattr(rpt, "contradictions"):
                issues = getattr(rpt, "contradictions")
            elif hasattr(rpt, "useless_policies"):
                issues = getattr(rpt, "useless_policies")
            else:
                issues = ()
            for iss in issues:
                raw.append(CorrectionProposal(description=str(iss), action="address_issue"))
        # De‑duplicate based on (description, action).
        uniq = { (p.description, p.action): p for p in raw }.values()
        # Deterministic ordering.
        sorted_props = tuple(sorted(uniq, key=lambda p: (p.description, p.action)))
        return CorrectionSet(proposals=sorted_props)
