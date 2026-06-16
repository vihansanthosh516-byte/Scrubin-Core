"""Adaptive deterministic planning package.

Exports the core public API for Phase 8.1:
    * ``AdaptiveManager`` – orchestrates the entire pipeline.
    * Model dataclasses – ``AdaptivePlan``, ``AdaptiveAction``, ``PolicyCandidate``,
      ``ContingencyPlan``, ``SimulationPreview``, ``AdaptiveSnapshot``.
"""

from .models import (
    AdaptiveAction,
    AdaptivePlan,
    PolicyCandidate,
    ContingencyPlan,
    SimulationPreview,
    AdaptiveSnapshot,
)
from .adaptive_manager import AdaptiveManager

__all__ = [
    "AdaptiveAction",
    "AdaptivePlan",
    "PolicyCandidate",
    "ContingencyPlan",
    "SimulationPreview",
    "AdaptiveSnapshot",
    "AdaptiveManager",
]
