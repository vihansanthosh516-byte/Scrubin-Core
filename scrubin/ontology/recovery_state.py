from __future__ import annotations

"""Immutable state representing active recovery protocols.

Only a minimal flag is required for the deterministic stub – ``salvage_active``
indicates whether a rescue pathway has been triggered.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RecoveryState:
    salvage_active: bool = False
    # Additional fields such as ``recovery_quality`` could be added later.

    def with_salvage_active(self, active: bool) -> "RecoveryState":
        return replace(self, salvage_active=active)
