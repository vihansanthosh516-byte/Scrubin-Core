from __future__ import annotations

"""Stub CognitiveState module for import compatibility.

The actual cognitive state logic lives in ``scrubin.world.state`` where a more
feature‑complete ``CognitiveState`` dataclass is defined.  This placeholder
ensures that importing ``scrubin.cognition.state`` does not raise an error in
contexts that only require the module to exist.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class CognitiveState:
    """Minimal frozen dataclass – fields are defined in ``scrubin.world.state``.
    """
    pass
