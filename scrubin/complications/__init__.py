"""Complications subsystem.

This package defines immutable data structures representing a medical
complication and a deterministic manager for their lifecycle.  The
implementation is deliberately side‑effect free – all operations return a
new :class:`ComplicationState` instance rather than mutating existing objects.
"""

from .models import Complication, ComplicationState, ComplicationEvent
from .manager import ComplicationManager

__all__ = [
    "Complication",
    "ComplicationState",
    "ComplicationEvent",
    "ComplicationManager",
]
