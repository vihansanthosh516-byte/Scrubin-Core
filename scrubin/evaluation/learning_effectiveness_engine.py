"""LearningEffectivenessEngine – evaluates the usefulness of learned policies.
All logic is deterministic and based solely on the supplied snapshot.
"""

from __future__ import annotations

from typing import Any

from .models import LearningEffectivenessReport


class LearningEffectivenessEngine:
    @staticmethod
    def evaluate(learning_snapshot: Any = None) -> LearningEffectivenessReport:
        """Assess learning subsystem.

        * ``useless_policies`` – policies with confidence <= 0.0.
        * ``stale_learning`` – policies whose ``last_used_tick`` is older than a
          hard‑coded threshold (e.g., 100 ticks).
        * ``over_generalization`` – policies whose ``scope`` attribute is the string
          ``"global"`` indicating overly broad rules.
        """
        useless = ()
        stale = ()
        overgen = ()
        if learning_snapshot is None:
            useless = ("missing_snapshot",)
        else:
            if hasattr(learning_snapshot, "policies"):
                for p in learning_snapshot.policies:
                    # confidence check
                    if getattr(p, "confidence", 1.0) <= 0.0:
                        useless = (*useless, getattr(p, "policy_id", str(p)))
                    # staleness check – assumes ``last_used_tick`` attribute exists
                    if getattr(p, "last_used_tick", 0) < getattr(learning_snapshot, "tick", 0) - 100:
                        stale = (*stale, getattr(p, "policy_id", str(p)))
                    # over‑generalisation check
                    if getattr(p, "scope", "") == "global":
                        overgen = (*overgen, getattr(p, "policy_id", str(p)))
        return LearningEffectivenessReport(
            useless_policies=useless,
            stale_learning=stale,
            over_generalization=overgen,
        )
