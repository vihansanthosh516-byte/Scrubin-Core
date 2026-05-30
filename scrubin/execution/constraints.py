from __future__ import annotations

"""Deterministic execution constraint predicates.

Each predicate receives the ``WorldState`` and returns ``True`` if the constraint
is satisfied.  When a constraint fails a deterministic timeline event is
emitted; the caller can decide to abort the maneuver.
"""

from typing import Callable, List

from scrubin.world.state import WorldState
from scrubin.core.events import TimelineEvent
from scrubin.execution.state import TechnicalExecutionState


def _emit(world: WorldState, description: str) -> WorldState:
    return world.append_timeline(TimelineEvent(world.tick, description))


def requires_visualization(world: WorldState) -> bool:
    tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
    if tech.visualization_quality < 0.4:
        world = _emit(world, "maneuver_blocked:requires_visualization")
        return False
    return True


def requires_exposure(world: WorldState) -> bool:
    tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
    if tech.exposure_quality < 0.3:
        world = _emit(world, "maneuver_blocked:requires_exposure")
        return False
    return True


def requires_hemostasis(world: WorldState) -> bool:
    # Placeholder: assume hemostasis is reflected in current risk level.
    tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
    if tech.current_risk_level > 0.6:
        world = _emit(world, "maneuver_blocked:requires_hemostasis")
        return False
    return True


def requires_instrument(world: WorldState, instrument: str) -> bool:
    tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
    if tech.active_instrument != instrument:
        world = _emit(world, f"maneuver_blocked:requires_instrument:{instrument}")
        return False
    return True


def prohibits_excess_force(world: WorldState, max_force: float = 1.0) -> bool:
    tech: TechnicalExecutionState = getattr(world, "technical_execution_state", TechnicalExecutionState())
    if tech.force_application > max_force:
        world = _emit(world, "unsafe_execution_attempt")
        return False
    return True
