"""MemoryAlignmentEngine – validates consistency of the memory subsystem.
The checks are deterministic and side‑effect free.
"""

from __future__ import annotations

from typing import Any

from .models import MemoryAlignmentReport


class MemoryAlignmentEngine:
    @staticmethod
    def evaluate(memory_snapshot: Any = None) -> MemoryAlignmentReport:
        """Detect memory alignment issues.

        * ``missing_snapshot`` when the snapshot is ``None``.
        * ``duplicate_episodes`` when the snapshot exposes an ``episodes``
          attribute with duplicate identifiers.
        """
        issues = ()
        if memory_snapshot is None:
            issues = ("missing_snapshot",)
        else:
            if hasattr(memory_snapshot, "episodes"):
                episodes = getattr(memory_snapshot, "episodes")
                ids = []
                for ep in episodes:
                    try:
                        ids.append(getattr(ep, "episode_id"))
                    except Exception:
                        ids.append(str(ep))
                if len(set(ids)) != len(ids):
                    issues = ("duplicate_episodes",)
        return MemoryAlignmentReport(issues=issues)
