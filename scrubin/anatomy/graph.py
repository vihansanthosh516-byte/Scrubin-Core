"""Deterministic anatomy graph utilities.

The graph is immutable – it stores a mapping from IDs to immutable
`AnatomicalStructure` objects.  All lookup methods return structures in
sorted deterministic order to guarantee replay‑able traversals.
"""

from __future__ import annotations

import hashlib
from typing import Tuple, Optional, List

from .models import AnatomicalStructure


class AnatomyGraph:
    """Immutable graph of anatomical structures.

    The graph is built from a tuple of ``AnatomicalStructure`` instances.
    All traversal methods return results sorted by structure ID to keep the
    order deterministic.
    """

    def __init__(self, structures: Tuple[AnatomicalStructure, ...]):
        # Internally store a dict for O(1) look‑ups; the dict itself is not
        # mutated after construction.
        self._structures = {s.id: s for s in structures}
        # Deterministic ordering of IDs for iteration / hash calculations.
        self._sorted_ids = tuple(sorted(self._structures.keys()))

    # ---------------------------------------------------------------------
    # Basic look‑ups
    # ---------------------------------------------------------------------
    def get(self, structure_id: str) -> AnatomicalStructure:
        return self._structures[structure_id]

    def parent(self, structure_id: str) -> Optional[AnatomicalStructure]:
        struct = self._structures.get(structure_id)
        if struct and struct.parent_id:
            return self._structures.get(struct.parent_id)
        return None

    def children(self, structure_id: str) -> Tuple[AnatomicalStructure, ...]:
        struct = self._structures.get(structure_id)
        if not struct:
            return ()
        childs = [self._structures[cid] for cid in struct.child_ids if cid in self._structures]
        # Deterministic order – sorted by ID.
        return tuple(sorted(childs, key=lambda s: s.id))

    def neighbors(self, structure_id: str) -> Tuple[AnatomicalStructure, ...]:
        neigh: List[AnatomicalStructure] = []
        parent = self.parent(structure_id)
        if parent:
            neigh.append(parent)
        neigh.extend(self.children(structure_id))
        # Sorting guarantees deterministic ordering.
        return tuple(sorted(neigh, key=lambda s: s.id))

    # ---------------------------------------------------------------------
    # Visibility helpers
    # ---------------------------------------------------------------------
    def exposed_structures(self) -> Tuple[AnatomicalStructure, ...]:
        expos = [s for s in self._structures.values() if s.visible]
        return tuple(sorted(expos, key=lambda s: s.id))

    def hidden_structures(self) -> Tuple[AnatomicalStructure, ...]:
        hidden = [s for s in self._structures.values() if not s.visible]
        return tuple(sorted(hidden, key=lambda s: s.id))

    # ---------------------------------------------------------------------
    # Deterministic hash of the entire graph – useful for replay certification.
    # ---------------------------------------------------------------------
    def deterministic_id(self) -> str:
        # Concatenate the deterministic IDs of all structures in sorted order.
        concat = "|".join(self._structures[sid].deterministic_id for sid in self._sorted_ids)
        return hashlib.sha256(concat.encode()).hexdigest()
