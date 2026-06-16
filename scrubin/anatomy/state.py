"""Immutable anatomy state model.

Provides ``AnatomicalState`` – top‑level container for anatomical regions – and
``AnatomicalRegion`` / ``Injury`` with deterministic IDs and immutable update
helpers (via ``replace``).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Tuple, List

# ---------------------------------------------------------------------------
# Injury definition – deterministic attributes for a tissue injury.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Injury:
    """Immutable injury record.

    * ``type`` – Injury type identifier (e.g., "vascular", "thermal").
    * ``severity`` – Float in [0,1] representing injury magnitude.
    * ``occult`` – Whether the injury is hidden initially.
    * ``onset_tick`` – Simulation tick at which injury occurred.
    * ``reveal_threshold`` – Ticks after which occult injury becomes visible.
    """
    type: str
    severity: float
    occult: bool = False
    onset_tick: int = 0
    reveal_threshold: int = 0
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [self.type, f"{self.severity:.5f}", str(self.occult), str(self.onset_tick), str(self.reveal_threshold)]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

    def with_occult(self, occult: bool) -> "Injury":
        return replace(self, occult=occult)

# ---------------------------------------------------------------------------
# Anatomical region – immutable representation of a discrete anatomical unit.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AnatomicalRegion:
    """Immutable representation of an anatomical region.

    * ``id`` – Unique identifier used for look‑ups.
    * ``name`` – Human readable name.
    * ``exposure`` – Float [0,1] indicating how much the region is exposed.
    * ``contamination`` – Boolean flag for contamination.
    * ``visualization_quality`` – Float [0,1] representing visual clarity.
    * ``accessible`` – Whether instruments can be applied.
    * ``injuries`` – Tuple of ``Injury`` objects attached to the region.
    * ``neighbors`` – Tuple of region IDs adjacent to this region.
    * ``ischemia`` – Boolean flag used by systems‑biology calculations.
    """
    id: str
    name: str = ""
    exposure: float = 0.0
    contamination: bool = False
    visualization_quality: float = 1.0
    accessible: bool = False
    injuries: Tuple[Injury, ...] = field(default_factory=tuple)
    neighbors: Tuple[str, ...] = field(default_factory=tuple)
    ischemia: bool = False
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [
            self.id,
            self.name,
            f"{self.exposure:.5f}",
            str(self.contamination),
            f"{self.visualization_quality:.5f}",
            str(self.accessible),
            "|".join(sorted(inj.deterministic_id for inj in self.injuries)),
            "|".join(sorted(self.neighbors)),
            str(self.ischemia),
        ]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

    # -------------------------------------------------------------------
    # Immutable helpers – return a new instance with updated fields.
    # -------------------------------------------------------------------
    def add_injury(self, inj: Injury) -> "AnatomicalRegion":
        return replace(self, injuries=self.injuries + (inj,))

    def with_injuries(self, injuries: Tuple[Injury, ...]) -> "AnatomicalRegion":
        return replace(self, injuries=injuries)

    def with_exposure(self, exposure: float) -> "AnatomicalRegion":
        return replace(self, exposure=exposure)

    def with_accessible(self, accessible: bool) -> "AnatomicalRegion":
        return replace(self, accessible=accessible)

    def with_visualization(self, quality: float) -> "AnatomicalRegion":
        return replace(self, visualization_quality=quality)

    def with_contamination(self, contamination: bool) -> "AnatomicalRegion":
        return replace(self, contamination=contamination)

# ---------------------------------------------------------------------------
# Top‑level anatomy container – immutable snapshot of all regions.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AnatomicalState:
    """Immutable collection of anatomical regions.

    ``regions`` is a tuple of ``AnatomicalRegion`` objects.  Deterministic ID is
    derived from the sorted deterministic IDs of all regions.
    """
    regions: Tuple[AnatomicalRegion, ...] = field(default_factory=tuple)
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic ordering – sort region IDs for hash stability.
        sorted_ids = sorted(region.deterministic_id for region in self.regions)
        concat = "|".join(sorted_ids)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(concat.encode()).hexdigest())

    # -------------------------------------------------------------------
    # Lookup helpers.
    # -------------------------------------------------------------------
    def get_region(self, region_id: str) -> AnatomicalRegion:
        for r in self.regions:
            if r.id == region_id:
                return r
        raise KeyError(f"Region {region_id} not found")

    # -------------------------------------------------------------------
    # Immutable update helpers.
    # -------------------------------------------------------------------
    def with_region(self, region: AnatomicalRegion) -> "AnatomicalState":
        # Replace or add the region by ID, keep deterministic ordering.
        new_regions = [r for r in self.regions if r.id != region.id]
        new_regions.append(region)
        # Sort by ID to guarantee deterministic order.
        new_regions_sorted = sorted(new_regions, key=lambda r: r.id)
        return replace(self, regions=tuple(new_regions_sorted))

    def with_updated_regions(self, updated: List[AnatomicalRegion]) -> "AnatomicalState":
        # Replace matching regions; any not present are added.
        region_map = {r.id: r for r in self.regions}
        for ur in updated:
            region_map[ur.id] = ur
        # Deterministic order – sort by ID.
        new_regions = tuple(sorted(region_map.values(), key=lambda r: r.id))
        return replace(self, regions=new_regions)

# ---------------------------------------------------------------------------
# TissueState – deterministic per‑structure state for interactions.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TissueState:
    """Immutable state of a tissue structure for deterministic interactions.

    Fields track simple binary flags representing modifications applied during
    interactions (cut, dissect, retract, etc.).
    """
    structure_id: str
    intact: bool = True
    dissected: bool = False
    retracted: bool = False
    cauterized: bool = False
    ligated: bool = False
    clipped: bool = False
    divided: bool = False
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        parts = [
            self.structure_id,
            str(self.intact),
            str(self.dissected),
            str(self.retracted),
            str(self.cauterized),
            str(self.ligated),
            str(self.clipped),
            str(self.divided),
        ]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())
