"""Node manager for distributed session ownership.

In a cluster each session is owned by exactly one node. Ownership is stored in a
shared key‑value store (simulated here with a simple in‑memory dict). The manager
provides deterministic claim/release semantics based on a hash‑ring routing
strategy.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional


class NodeRegistry:
    """Registry of active node identifiers.

    ``node_id`` is an opaque string (e.g. container hostname). The registry is
    used to compute deterministic routing via ``hash(session_id) % len(nodes)``.
    """

    def __init__(self) -> None:
        self._nodes: List[str] = []
        # Mapping ``session_id`` → owning ``node_id``
        self._ownership: Dict[str, str] = {}

    def register_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            self._nodes.append(node_id)
            self._nodes.sort()  # deterministic ordering for routing

    def unregister_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            self._nodes.remove(node_id)
            # Release any sessions owned by this node
            to_release = [s for s, o in self._ownership.items() if o == node_id]
            for s in to_release:
                del self._ownership[s]

    def list_nodes(self) -> List[str]:
        return list(self._nodes)

    # ---------------------------------------------------------------------
    # Ownership operations
    # ---------------------------------------------------------------------
    def claim(self, session_id: str, requester: str) -> bool:
        """Attempt to claim ownership of ``session_id`` for ``requester``.

        Returns ``True`` if the claim succeeded, ``False`` otherwise.
        """
        owner = self._ownership.get(session_id)
        if owner is None:
            # No owner – assign to requester
            self._ownership[session_id] = requester
            return True
        if owner == requester:
            return True
        return False

    def release(self, session_id: str, requester: str) -> bool:
        owner = self._ownership.get(session_id)
        if owner == requester:
            del self._ownership[session_id]
            return True
        return False

    def get_owner(self, session_id: str) -> Optional[str]:
        return self._ownership.get(session_id)

    def deterministic_node(self, session_id: str) -> Optional[str]:
        """Deterministically select a node based on the session id.

        Returns ``None`` if no nodes are registered.
        """
        if not self._nodes:
            return None
        # Use a stable hash (SHA‑256) to avoid Python's hash randomisation.
        h = int(hashlib.sha256(session_id.encode("utf-8")).hexdigest(), 16)
        idx = h % len(self._nodes)
        return self._nodes[idx]
