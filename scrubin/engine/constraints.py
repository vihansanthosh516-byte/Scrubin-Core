"""Constraint system for declarative, composable procedural predicates.

All constraints operate on the immutable :class:`scrubin.world.state.WorldState`
and return a boolean.  They are deliberately side‑effect free – the evaluation
does not mutate the world.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List

from scrubin.world.state import WorldState


class Constraint(ABC):
    """Abstract base class for all procedural predicates.

    Sub‑classes must implement :meth:`evaluate` which receives a ``WorldState``
    and returns ``True``/``False``.
    """

    @abstractmethod
    def evaluate(self, world: WorldState) -> bool:
        ...

    # ---------------------------------------------------------------------
    # Logical combinators – these return new ``Constraint`` objects that wrap the
    # original ones.  They allow arbitrary boolean expressions to be built.
    # ---------------------------------------------------------------------
    def __and__(self, other: "Constraint") -> "Constraint":
        return And(self, other)

    def __or__(self, other: "Constraint") -> "Constraint":
        return Or(self, other)

    def __invert__(self) -> "Constraint":
        return Not(self)


# -------------------------------------------------------------------------
# Concrete primitive constraints
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class HemodynamicStable(Constraint):
    """True if vital signs are within a stable range.

    Simplified check: heart rate between 60‑100 and systolic bp > 90.
    """
    hr_low: int = 60
    hr_high: int = 100
    sbp_min: int = 90

    def evaluate(self, world: WorldState) -> bool:
        vit = world.physiology.vitals
        return self.hr_low <= vit.heart_rate <= self.hr_high and vit.bp_systolic >= self.sbp_min


@dataclass(frozen=True)
class ExposureEstablished(Constraint):
    """True if a named anatomical exposure flag is present in ``world.anatomical_exposures``.

    The ``WorldState`` does not currently expose a dedicated attribute; for the
    purpose of this demonstration we use ``world.cognitive`` as a placeholder
    where ``available_options`` can encode exposures.
    """
    exposure_name: str

    def evaluate(self, world: WorldState) -> bool:
        # Placeholder implementation – assumes exposure names are stored in
        # ``world.cognitive.available_options`` as a convention.
        return self.exposure_name in world.cognitive.available_options


@dataclass(frozen=True)
class NoActiveHemorrhage(Constraint):
    """True if no active complication with id ``"hemorrhage"`` is present."""

    def evaluate(self, world: WorldState) -> bool:
        return all(comp.id != "hemorrhage" for comp in world.complications.active)


@dataclass(frozen=True)
class VisualizationAdequate(Constraint):
    """True if a generic visualization score meets or exceeds ``threshold``.

    The ``WorldState`` currently does not store a dedicated visualization metric;
    we approximate using ``world.scoring.hemodynamic`` as a proxy.
    """
    threshold: float = 0.5

    def evaluate(self, world: WorldState) -> bool:
        return world.scoring.hemodynamic >= self.threshold


@dataclass(frozen=True)
class ContaminationBelowThreshold(Constraint):
    """True if the contamination score is below ``max_allowed``.
    """
    max_allowed: float = 0.2

    def evaluate(self, world: WorldState) -> bool:
        return world.scoring.contamination < self.max_allowed


@dataclass(frozen=True)
class ResourceAvailable(Constraint):
    """True if a named resource has a positive amount.
    """
    resource_name: str

    def evaluate(self, world: WorldState) -> bool:
        resources = dict(world.resources.resources)
        return resources.get(self.resource_name, 0) > 0


@dataclass(frozen=True)
class HiddenEffectPresent(Constraint):
    """True if a hidden effect with the given ``effect_id`` is registered.
    """
    effect_id: str

    def evaluate(self, world: WorldState) -> bool:
        return any(getattr(he, "id", None) == self.effect_id for he in world.hidden_effects)


@dataclass(frozen=True)
class PhaseCompleted(Constraint):
    """Proxy that forwards to a specific ``ProcedurePhase``'s ``can_complete``.
    """
    phase: "ProcedurePhase"

    def evaluate(self, world: WorldState) -> bool:
        return self.phase.can_complete(world)


@dataclass(frozen=True)
class TimeBelowLimit(Constraint):
    """True if the current tick is less than ``limit``.
    """
    limit: int

    def evaluate(self, world: WorldState) -> bool:
        return world.tick < self.limit


# -------------------------------------------------------------------------
# Logical combinators – ``And``, ``Or``, ``Not``
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class And(Constraint):
    left: Constraint
    right: Constraint

    def evaluate(self, world: WorldState) -> bool:
        return self.left.evaluate(world) and self.right.evaluate(world)


@dataclass(frozen=True)
class Or(Constraint):
    left: Constraint
    right: Constraint

    def evaluate(self, world: WorldState) -> bool:
        return self.left.evaluate(world) or self.right.evaluate(world)


@dataclass(frozen=True)
class Not(Constraint):
    operand: Constraint

    def evaluate(self, world: WorldState) -> bool:
        return not self.operand.evaluate(world)
