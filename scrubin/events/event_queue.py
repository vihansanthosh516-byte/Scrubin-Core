"""Deterministic priority queue for surgical events.

The queue orders events first by tick, then by priority (lower first), then by
event_type, and finally by event_id.  This ordering guarantees deterministic
behaviour across runs and platforms.
"""

import heapq
from typing import List

from .event import SurgicalEvent


class EventQueue:
    """A deterministic priority queue for ``SurgicalEvent`` objects.

    The internal heap stores a tuple ``(tick, priority, event_type, event_id,
    event)`` which defines the deterministic ordering.  The ``add`` method
    pushes a new event, and ``pop_all_up_to_tick`` extracts events whose tick is
    less than or equal to the supplied value.
    """

    def __init__(self) -> None:
        self._heap: List[tuple] = []

    def add(self, event: SurgicalEvent) -> None:
        """Insert ``event`` into the queue.

        The event is ordered by ``(tick, priority, event_type, event_id)``.
        """
        heapq.heappush(
            self._heap,
            (event.tick, event.priority, event.event_type, event.event_id, event),
        )

    def pop_all_up_to_tick(self, tick: int) -> List[SurgicalEvent]:
        """Remove and return all events with ``event.tick`` <= ``tick``.

        Returned events are sorted deterministically by the same criteria used
        for the heap ordering.
        """
        events: List[SurgicalEvent] = []
        while self._heap and self._heap[0][0] <= tick:
            _, _, _, _, ev = heapq.heappop(self._heap)
            events.append(ev)
        # ``events`` are already in deterministic order because they were
        # popped from a heap respecting the tuple ordering.
        return events

    def __len__(self) -> int:
        return len(self._heap)

    def __iter__(self):
        """Iterate over the queued events in deterministic order without
        removing them.
        """
        return (item[4] for item in sorted(self._heap))
