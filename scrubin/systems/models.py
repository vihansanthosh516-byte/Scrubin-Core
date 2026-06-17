"""Immutable dataclasses representing individual organ systems.

Each system is a frozen ``@dataclass`` with ``slots=True``.  All fields are
primitive (int/float/bool/str) and therefore hashable.  Updates are performed
solely with ``dataclasses.replace`` – no mutation.

The module also defines a container ``SystemsState`` that aggregates the eight
systems in a deterministic order.  ``deterministic_hash`` for each system and
for the aggregate state is a simple ``hash`` of a tuple of its fields – this is
stable for a given interpreter session (the tests compare hashes within the
same process).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple

# ---------------------------------------------------------------------------
# Base system – shared fields
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BaseSystem:
    deterministic_id: int
    status: str = "normal"
    reserve_capacity: float = 1.0  # 0‑1 proportion of reserve resources
    compensation_level: float = 0.0
    perfusion: float = 1.0  # 0‑1 proportion of ideal perfusion
    oxygen_delivery: float = 1.0
    oxygen_consumption: float = 1.0
    stress_level: float = 0.0
    failure_state: bool = False

    @property
    def deterministic_hash(self) -> int:
        """Deterministic hash based on all primitive fields.

        The built‑in ``hash`` is deterministic for the lifetime of the Python
        process (the test suite runs in a single process), which matches the
        existing style used elsewhere in the code base.
        """
        return hash(
            (
                self.deterministic_id,
                self.status,
                self.reserve_capacity,
                self.compensation_level,
                self.perfusion,
                self.oxygen_delivery,
                self.oxygen_consumption,
                self.stress_level,
                self.failure_state,
            )
        )

# ---------------------------------------------------------------------------
# Specific organ systems – subclasses of BaseSystem
# ---------------------------------------------------------------------------

# Cardiovascular system carries additional haemodynamic parameters.
@dataclass(frozen=True, slots=True)
class CardiovascularSystem(BaseSystem):
    # Deterministic identifier – fixed for this subclass.
    deterministic_id: int = 1
    # Haemodynamic parameters (defaults represent a healthy adult).
    map: float = 100.0  # mean arterial pressure (mmHg)
    cardiac_output: float = 5.0  # L/min
    vascular_resistance: float = 1.0  # arbitrary unit
    blood_loss: float = 0.0  # ml loss as proportion of total blood volume
    vasopressor_support: float = 0.0  # 0‑1 intensity of pharmacologic support

    @property
    def deterministic_hash(self) -> int:
        # Compute hash over all fields (base + cardiovascular‑specific).
        return hash(
            (
                self.deterministic_id,
                self.status,
                self.reserve_capacity,
                self.compensation_level,
                self.perfusion,
                self.oxygen_delivery,
                self.oxygen_consumption,
                self.stress_level,
                self.failure_state,
                self.map,
                self.cardiac_output,
                self.vascular_resistance,
                self.blood_loss,
                self.vasopressor_support,
            )
        )

# Other organ systems use the base fields without extra parameters.
@dataclass(frozen=True, slots=True)
class RespiratorySystem(BaseSystem):
    deterministic_id: int = 2

@dataclass(frozen=True, slots=True)
class RenalSystem(BaseSystem):
    deterministic_id: int = 3

@dataclass(frozen=True, slots=True)
class HepaticSystem(BaseSystem):
    deterministic_id: int = 4

@dataclass(frozen=True, slots=True)
class NeurologicSystem(BaseSystem):
    deterministic_id: int = 5

@dataclass(frozen=True, slots=True)
class EndocrineSystem(BaseSystem):
    deterministic_id: int = 6

@dataclass(frozen=True, slots=True)
class ImmuneSystem(BaseSystem):
    deterministic_id: int = 7

# Metabolic system includes extra fields for lactate and acidosis.
@dataclass(frozen=True, slots=True)
class MetabolicSystem(BaseSystem):
    deterministic_id: int = 8
    lactate: float = 0.0
    acidosis: float = 0.0

    @property
    def deterministic_hash(self) -> int:
        # Include base fields plus lactate and acidosis.
        return hash(
            (
                self.deterministic_id,
                self.status,
                self.reserve_capacity,
                self.compensation_level,
                self.perfusion,
                self.oxygen_delivery,
                self.oxygen_consumption,
                self.stress_level,
                self.failure_state,
                self.lactate,
                self.acidosis,
            )
        )

# ---------------------------------------------------------------------------
# Aggregate state
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SystemsState:
    """Container for the deterministic snapshot of all organ systems.

    The ordering of fields in the dataclass defines the deterministic ordering
    for the aggregate hash.
    """

    cardiovascular: CardiovascularSystem
    respiratory: RespiratorySystem
    renal: RenalSystem
    hepatic: HepaticSystem
    neurologic: NeurologicSystem
    endocrine: EndocrineSystem
    immune: ImmuneSystem
    metabolic: MetabolicSystem

    @property
    def deterministic_hash(self) -> int:
        # Hash of the subsystem objects (or placeholders) in deterministic order.
        return hash((
            self.cardiovascular,
            self.respiratory,
            self.renal,
            self.hepatic,
            self.neurologic,
            self.endocrine,
            self.immune,
            self.metabolic,
        ))
