# Timeline query engine – deterministic filtering of timeline events.
"""
Provides a ``query_timeline`` helper that filters ``TimelineEvent`` objects
from a ``WorldState`` (or dict snapshot) based on a user‑supplied predicate.
"""

from __future__ import annotations

from typing import Callable, List, Any

# ``TimelineEvent`` is defined in ``scrubin.core.events`` but we keep the import
# optional to avoid hard dependencies on the full simulation engine.
try:
    from scrubin.core.events import TimelineEvent
except Exception:  # pragma: no cover
    TimelineEvent = Any  # type: ignore


def query_timeline(world: Any, predicate: Callable[[TimelineEvent], bool]) -> List[TimelineEvent]:
    """Return all timeline events from ``world`` that satisfy ``predicate``.

    The ``world`` argument may be a ``WorldState`` instance or a dict‑like snapshot
    that contains a ``timeline`` attribute/key holding an iterable of
    ``TimelineEvent`` objects (or dicts with a ``description`` field).
    """
    # Resolve the timeline collection.
    timeline: List[TimelineEvent] = []
    if hasattr(world, "timeline"):
        timeline = list(getattr(world, "timeline"))
    elif isinstance(world, dict):
        timeline = world.get("timeline", [])
    # Apply the predicate.
    return [event for event in timeline if predicate(event)]
