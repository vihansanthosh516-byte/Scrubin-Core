"""Immutable anatomy model definitions for deterministic simulation.

Each anatomical structure is a frozen dataclass with a deterministic identifier
computed from its core fields.  Subclasses represent specific tissue types but
share the same base attributes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, Optional

# ---------------------------------------------------------------------------
# Base anatomical structure – common fields for all tissue types.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AnatomicalStructure:
    """Base class for all anatomical entities.

    * ``id`` – Unique identifier within the anatomy graph.
    * ``name`` – Human‑readable name (optional).
    * ``parent_id`` – Identifier of the parent structure (if any).
    * ``child_ids`` – Tuple of identifiers of direct children.
    * ``layer`` – Anatomical layer (e.g., "muscular", "visceral").
    * ``blood_supply`` – Name of supplying vessel or arterial branch.
    * ``innervation`` – Name of supplying nerve.
    * ``structural_integrity`` – Float in [0,1] representing health.
    * ``visible`` – Whether the structure is currently visible.
    * ``accessible`` – Whether the structure can be accessed by instruments.
    * ``attached_ids`` – Tuple of identifiers of attached structures.
    """

    id: str
    name: str = ""
    parent_id: Optional[str] = None
    child_ids: Tuple[str, ...] = field(default_factory=tuple)
    layer: str = ""
    blood_supply: str = ""
    innervation: str = ""
    structural_integrity: float = 1.0
    visible: bool = False
    accessible: bool = False
    attached_ids: Tuple[str, ...] = field(default_factory=tuple)
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Deterministic identifier based on immutable fields.
        parts = [
            self.id,
            self.name,
            self.parent_id or "",
            "|".join(sorted(self.child_ids)),
            self.layer,
            self.blood_supply,
            self.innervation,
            f"{self.structural_integrity:.5f}",
            str(self.visible),
            str(self.accessible),
            "|".join(sorted(self.attached_ids)),
        ]
        combined = "|".join(parts)
        object.__setattr__(self, "deterministic_id", hashlib.sha256(combined.encode()).hexdigest())

# ---------------------------------------------------------------------------
# Specific structure subclasses – currently no extra fields but allow type checks.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Organ(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Vessel(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Nerve(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Fascia(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Muscle(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Ligament(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Mesentery(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Duct(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class Cavity(AnatomicalStructure):
    pass

@dataclass(frozen=True, slots=True)
class TissuePlane(AnatomicalStructure):
    pass
