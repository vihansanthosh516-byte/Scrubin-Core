from __future__ import annotations

"""Immutable operator skill profile used by deterministic execution engines.

All skill attributes are normalized to the range 0.0‑1.0 where higher values
represent better ability.  The profile is immutable; ``with_*`` helpers return a
new instance via ``replace``.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class OperatorSkillProfile:
    dexterity: float = 1.0
    steadiness: float = 1.0
    laparoscopic_skill: float = 1.0
    open_skill: float = 1.0
    vascular_skill: float = 1.0
    tissue_respect: float = 1.0
    instrument_familiarity: float = 1.0
    adaptability: float = 1.0
    stress_tolerance: float = 1.0
    fatigue_resistance: float = 1.0
    recovery_capability: float = 1.0

    # ---------------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable instance.
    # ---------------------------------------------------------------------
    def with_dexterity(self, value: float) -> "OperatorSkillProfile":
        return replace(self, dexterity=max(0.0, min(1.0, value)))

    def with_steadiness(self, value: float) -> "OperatorSkillProfile":
        return replace(self, steadiness=max(0.0, min(1.0, value)))

    def with_laparoscopic_skill(self, value: float) -> "OperatorSkillProfile":
        return replace(self, laparoscopic_skill=max(0.0, min(1.0, value)))

    def with_open_skill(self, value: float) -> "OperatorSkillProfile":
        return replace(self, open_skill=max(0.0, min(1.0, value)))

    def with_vascular_skill(self, value: float) -> "OperatorSkillProfile":
        return replace(self, vascular_skill=max(0.0, min(1.0, value)))

    def with_tissue_respect(self, value: float) -> "OperatorSkillProfile":
        return replace(self, tissue_respect=max(0.0, min(1.0, value)))

    def with_instrument_familiarity(self, value: float) -> "OperatorSkillProfile":
        return replace(self, instrument_familiarity=max(0.0, min(1.0, value)))

    def with_adaptability(self, value: float) -> "OperatorSkillProfile":
        return replace(self, adaptability=max(0.0, min(1.0, value)))

    def with_stress_tolerance(self, value: float) -> "OperatorSkillProfile":
        return replace(self, stress_tolerance=max(0.0, min(1.0, value)))

    def with_fatigue_resistance(self, value: float) -> "OperatorSkillProfile":
        return replace(self, fatigue_resistance=max(0.0, min(1.0, value)))

    def with_recovery_capability(self, value: float) -> "OperatorSkillProfile":
        return replace(self, recovery_capability=max(0.0, min(1.0, value)))
