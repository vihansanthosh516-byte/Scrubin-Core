from __future__ import annotations

"""Placeholder procedural memory module.

The original codebase references ``scrubin.cognition.procedural_memory`` but the
module does not exist in the repository.  For deterministic execution we provide a
minimal immutable dataclass that satisfies imports without adding behaviour.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple, Any


@dataclass(frozen=True)
class ProceduralMemory:
    """Immutable container for serialised procedural memories.

    At the moment the engine does not rely on stored memories; the field is kept
    for compatibility with the existing ``WorldState`` definition.
    """

    episodes: Tuple[Any, ...] = field(default_factory=tuple)

    def with_episodes(self, episodes: Tuple[Any, ...]) -> "ProceduralMemory":
        """Return a new ``ProceduralMemory`` with the supplied episodes.

        ``episodes`` replaces the existing tuple – the operation is deterministic
        because the tuple ordering is preserved.
        """
        return replace(self, episodes=episodes)
