"""Simple deterministic importance scoring for episodes.

The importance model is deliberately lightweight – it assigns a higher score
to ticks that contain complications and a modest score for physiology changes
or actions. The result is normalised to the range ``0.0`` – ``1.0``.
"""

from __future__ import annotations

from typing import List

from scrubin.events import event_types
from scrubin.events.event import SurgicalEvent


def compute_importance(events: List[SurgicalEvent]) -> float:
    """Deterministically compute a float importance score for a tick.

    The scoring rules are:
    * ``COMPLICATION_EVENT`` → +1.0 per event
    * ``PHYSIOLOGY_EVENT``   → +0.2 per event
    * ``ACTION_EVENT``        → +0.1 per event
    The raw total is normalised by dividing by ``10.0`` and capped at ``1.0``.
    """
    weight = 0.0
    for ev in events:
        if ev.event_type == event_types.COMPLICATION_EVENT:
            weight += 1.0
        elif ev.event_type == event_types.PHYSIOLOGY_EVENT:
            weight += 0.2
        elif ev.event_type == event_types.ACTION_EVENT:
            weight += 0.1
    # Normalise to 0‑1 range – deterministic scaling factor 10.0 chosen
    normalized = weight / 10.0
    return min(normalized, 1.0)
