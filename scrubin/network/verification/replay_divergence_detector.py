"""Replay Divergence Detector – detects divergence between two hash chains.

Given two network hash chains, the detector records any tick where the hashes differ.
Outputs a frozen ``DivergenceReport`` containing deterministic IDs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

# ---------------------------------------------------------------------------
# Result structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DivergencePoint:
    """Immutable description of a divergence at a specific tick."""
    tick: int
    hash_a: str
    hash_b: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.tick}|{self.hash_a}|{self.hash_b}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class DivergenceReport:
    """Aggregated report of all divergence points between two runs."""
    points: Tuple[DivergencePoint, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        ids = "|".join(p.deterministic_id for p in self.points)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(ids.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Detector implementation
# ---------------------------------------------------------------------------

class ReplayDivergenceDetector:
    """Detects divergence between two network hash chains.

    ``detect`` returns a ``DivergenceReport``.  The comparison stops at the
    shorter chain length; any extra ticks in the longer chain are ignored for the
    purpose of this simple deterministic implementation.
    """

    @staticmethod
    def detect(chain_a: List[Dict], chain_b: List[Dict]) -> DivergenceReport:
        points: List[DivergencePoint] = []
        length = min(len(chain_a), len(chain_b))
        for i in range(length):
            entry_a = chain_a[i]
            entry_b = chain_b[i]
            if entry_a.get("hash") != entry_b.get("hash"):
                points.append(
                    DivergencePoint(
                        tick=entry_a.get("tick", i + 1),
                        hash_a=entry_a.get("hash", ""),
                        hash_b=entry_b.get("hash", ""),
                    )
                )
        return DivergenceReport(points=tuple(points))
