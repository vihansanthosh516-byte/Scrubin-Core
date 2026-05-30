from __future__ import annotations
"""Deterministic event deduplication utilities.

Repeated low‑impact events (e.g. frequent friction or overload warnings) can
quickly inflate the ``WorldState.timeline``.  The ``deduplicate_events`` function
compresses consecutive identical low‑value events into a single sentinel event
while preserving the original tick for ordering.
"""

from typing import Tuple, Set

from scrubin.core.events import TimelineEvent

# Define which event descriptions are considered low‑value and eligible for
# compression.  This list can be extended as the engine evolves.
_LOW_VALUE_DESCRIPTIONS: Set[str] = {
    "workflow_friction_increased",
    "overload_warning",
    "compensation_started:cardiovascular",
    "compensation_started:respiratory",
    # Add other frequently emitted events here.
}


def deduplicate_events(timeline: Tuple[TimelineEvent, ...]) -> Tuple[TimelineEvent, ...]:
    """Compress consecutive low‑value events.

    For each block of identical consecutive events whose description is present in
    ``_LOW_VALUE_DESCRIPTIONS`` and whose length exceeds one, the block is
    replaced by a single event with the description ``"{desc}_persistent"``.  The
    tick of the new event is the tick of the first event in the block, preserving
    deterministic ordering.
    """
    if not timeline:
        return timeline

    result: list[TimelineEvent] = []
    i = 0
    n = len(timeline)
    while i < n:
        cur = timeline[i]
        # Count how many consecutive events share the same description.
        j = i + 1
        while j < n and timeline[j].description == cur.description:
            j += 1
        block_len = j - i
        if block_len > 1 and cur.description in _LOW_VALUE_DESCRIPTIONS:
            # Replace the block with a persistent marker.
            new_desc = f"{cur.description}_persistent"
            result.append(TimelineEvent(tick=cur.tick, description=new_desc))
        else:
            # Keep all events in the block.
            result.extend(timeline[i:j])
        i = j
    return tuple(result)
