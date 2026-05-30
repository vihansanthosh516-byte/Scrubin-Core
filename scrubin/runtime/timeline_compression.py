from __future__ import annotations
"""Deterministic timeline compression utilities.

Long simulations can generate a large number of timeline events.  The helper
functions below provide a simple, deterministic way to reduce the size of the
timeline while preserving the ordering and overall semantic information.
"""

from typing import Tuple

from scrubin.core.events import TimelineEvent


def compress_timeline(timeline: Tuple[TimelineEvent, ...]) -> Tuple[TimelineEvent, ...]:
    """Compress the timeline by merging events that occur on the same tick.

    All events sharing a tick are combined into a single ``TimelineEvent`` whose
    description concatenates the unique original descriptions (sorted for
    determinism) separated by semicolons.  The resulting timeline contains at most
    one event per tick, guaranteeing a worst‑case linear size in the number of
    ticks rather than the number of emitted events.
    """
    if not timeline:
        return timeline
    compressed: list[TimelineEvent] = []
    i = 0
    n = len(timeline)
    while i < n:
        cur_tick = timeline[i].tick
        descriptions = set()
        while i < n and timeline[i].tick == cur_tick:
            descriptions.add(timeline[i].description)
            i += 1
        merged_desc = ";".join(sorted(descriptions))
        compressed.append(TimelineEvent(tick=cur_tick, description=merged_desc))
    return tuple(compressed)
