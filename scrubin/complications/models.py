'''Immutable complication model for deterministic simulation.

All fields are frozen dataclasses; any change must be performed via
``dataclasses.replace`` which returns a new instance. The model contains a
``deterministic_id`` that is a SHA‑256 hash of the immutable fields; this is
used by the replay‑hash system to guarantee that two identical complication
states produce identical hashes.
'''

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, Any


@dataclass(frozen=True, slots=True)
class Complication:
    """Deterministic complication definition.

    * ``id`` – unique identifier for the complication.
    * ``type`` – high‑level category (e.g., "arterial_bleeding").
    * ``trigger`` – step ID that activates the complication.
    * ``resolution`` – step ID that resolves the complication.
    * ``severity`` – numeric severity score (0.0 … 1.0).
    * ``affected_regions`` – identifiers of anatomy regions impacted.
    * ``physiology_effects`` – tuple of (key, delta) pairs applied to physiology.
    * ``anatomy_effects`` – tuple of (key, delta) pairs applied to anatomy.
    * ``team_requirements`` – additional team resources needed.
    * ``progression_rate`` – severity increase per tick while active.
    * ``recovery_rate`` – severity decrease per successful intervention.
    * ``active`` – whether the complication is currently active.
    * ``resolved`` – whether it has been resolved.
    """

    id: str
    type: str
    trigger: str
    resolution: str
    severity: float = 0.0
    affected_regions: Tuple[str, ...] = field(default_factory=tuple)
    physiology_effects: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)
    anatomy_effects: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)
    team_requirements: Tuple[str, ...] = field(default_factory=tuple)
    progression_rate: float = 0.0
    recovery_rate: float = 0.0
    active: bool = False
    resolved: bool = False
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # Compute deterministic identifier based on immutable content.
        parts = [
            self.id,
            self.type,
            self.trigger,
            self.resolution,
            f"{self.severity:.6f}",
            ",".join(self.affected_regions),
            ",".join(f"{k}:{v}" for k, v in self.physiology_effects),
            ",".join(f"{k}:{v}" for k, v in self.anatomy_effects),
            ",".join(self.team_requirements),
            f"{self.progression_rate:.6f}",
            f"{self.recovery_rate:.6f}",
            str(self.active),
            str(self.resolved),
        ]
        digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
        object.__setattr__(self, "deterministic_id", digest)
