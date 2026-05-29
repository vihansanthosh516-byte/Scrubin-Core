"""Immutable anatomical state model.

The model represents a deterministic, immutable view of the operative
anatomy.  Each anatomical region is a frozen dataclass; the container
`AnatomicalState` holds a tuple of all regions and provides ``with_*`` helpers that
return new instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Tuple, List


# ---------------------------------------------------------------------------
# Basic injury representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Injury:
    """Simple injury descriptor.

    * ``type`` – e.g. ``"thermal"``, ``"vascular"``.
    * ``severity`` – float 0‑1.
    * ``occult`` – if ``True`` the injury is hidden until its reveal threshold.
    * ``onset_tick`` – tick at which the injury occurred.
    * ``reveal_threshold`` – number of ticks after which the occult injury becomes visible.
    """
    type: str
    severity: float = 0.0
    occult: bool = True
    onset_tick: int = 0
    reveal_threshold: int = 0

    def with_occult(self, occult: bool) -> "Injury":
        return replace(self, occult=occult)

    def with_severity(self, severity: float) -> "Injury":
        return replace(self, severity=severity)


# ---------------------------------------------------------------------------
# Anatomical region model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnatomicalRegion:
    """Immutable representation of a single anatomical structure.

    Attributes capture exposure, visualization, injury, contamination, ischemia,
    accessibility and procedural relevance.  ``neighbors`` stores the IDs of
    adjacent structures – the adjacency graph is defined elsewhere (topology).
    """
    id: str
    name: str
    exposure: float = 0.0  # 0.0 hidden → 1.0 fully exposed
    visualization_quality: float = 1.0  # 0.0 – 1.0
    injuries: Tuple[Injury, ...] = field(default_factory=tuple)
    contamination: bool = False
    ischemia: bool = False
    accessible: bool = False
    manipulation_history: Tuple[str, ...] = field(default_factory=tuple)
    neighbors: Tuple[str, ...] = field(default_factory=tuple)

    # ---------------------------------------------------------------------
    # Helper methods – each returns a new instance
    # ---------------------------------------------------------------------
    def with_exposure(self, exposure: float) -> "AnatomicalRegion":
        return replace(self, exposure=exposure)

    def with_visualization(self, quality: float) -> "AnatomicalRegion":
        return replace(self, visualization_quality=quality)

    def with_injuries(self, injuries: Tuple[Injury, ...]) -> "AnatomicalRegion":
        return replace(self, injuries=injuries)

    def add_injury(self, injury: Injury) -> "AnatomicalRegion":
        return replace(self, injuries=self.injuries + (injury,))

    def with_contamination(self, flag: bool) -> "AnatomicalRegion":
        return replace(self, contamination=flag)

    def with_ischemia(self, flag: bool) -> "AnatomicalRegion":
        return replace(self, ischemia=flag)

    def with_accessible(self, flag: bool) -> "AnatomicalRegion":
        return replace(self, accessible=flag)

    def add_manipulation(self, action: str) -> "AnatomicalRegion":
        return replace(self, manipulation_history=self.manipulation_history + (action,))

    def with_neighbors(self, neighbors: Tuple[str, ...]) -> "AnatomicalRegion":
        return replace(self, neighbors=neighbors)


# ---------------------------------------------------------------------------
# Container for all anatomical regions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnatomicalState:
    """Immutable collection of all anatomical regions.

    The ``regions`` tuple is ordered deterministically; look‑ups are O(n) but the
    size is small enough for the educational simulation.
    """
    regions: Tuple[AnatomicalRegion, ...] = field(default_factory=tuple)

    def get_region(self, region_id: str) -> AnatomicalRegion:
        for r in self.regions:
            if r.id == region_id:
                return r
        raise KeyError(f"Anatomical region '{region_id}' not found")

    def with_region(self, region: AnatomicalRegion) -> "AnatomicalState":
        # Replace the region with matching ID, preserving deterministic ordering.
        filtered = tuple(r for r in self.regions if r.id != region.id)
        return replace(self, regions=filtered + (region,))

    def with_updated_regions(self, updates: List[AnatomicalRegion]) -> "AnatomicalState":
        # Apply a batch of region updates.
        new_state = self
        for reg in updates:
            new_state = new_state.with_region(reg)
        return new_state
