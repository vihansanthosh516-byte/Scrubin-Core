"""Deterministic agent scheduler utilities.

Only a very small helper is needed for the current tests – order agents by
``priority`` then ``agent_id``.
"""

from __future__ import annotations

from typing import List

from .agents.base_agent import CognitiveAgent


def deterministic_order(agents: List[CognitiveAgent]) -> List[CognitiveAgent]:
    """Return agents ordered deterministically.

    Lower ``priority`` runs first; ties are broken by ``agent_id`` lexical order.
    """
    return sorted(agents, key=lambda a: (a.priority, a.agent_id))
