"""Deterministic anatomical adjacency topology.

The topology maps each anatomical region ID to a tuple of neighboring region IDs.
It is used by the exposure and injury propagation engines to determine local
effects (exposure spill‑over, contamination spread, injury propagation, etc.).
"""

from __future__ import annotations

from typing import Dict, Tuple

# Example topology for an appendectomy scenario.
# In a real system this would be generated from an anatomical ontology.
DEFAULT_TOPOLOGY: Dict[str, Tuple[str, ...]] = {
    "appendix": ("mesoappendix",),
    "mesoappendix": ("appendix", "appendiceal_artery", "cecum"),
    "appendiceal_artery": ("mesoappendix",),
    "cecum": ("mesoappendix", "terminal_ileum"),
    "terminal_ileum": ("cecum",),
}

def apply_topology(regions: Tuple["AnatomicalRegion", ...]) -> Tuple["AnatomicalRegion", ...]:
    """Assign neighbor relationships to each region based on ``DEFAULT_TOPOLOGY``.

    Returns a new tuple of ``AnatomicalRegion`` objects with the ``neighbors``
    field populated.
    """
    from .state import AnatomicalRegion
    updated: list[AnatomicalRegion] = []
    for region in regions:
        neigh = DEFAULT_TOPOLOGY.get(region.id, ())
        updated.append(region.with_neighbors(tuple(neigh)))
    return tuple(updated)
