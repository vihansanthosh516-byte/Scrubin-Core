from __future__ import annotations

"""Technical execution state for deterministic surgical maneuver handling.

All fields are immutable; updates are performed via ``with_*`` helpers that
return a new ``TechnicalExecutionState`` instance using ``replace``.
"""

from dataclasses import dataclass, field, replace
from typing import Tuple


@dataclass(frozen=True)
class TechnicalExecutionState:
    """Immutable representation of the current technical execution context.

    The fields mirror the detailed execution metrics required by the
    deterministic kernel.  Default values are chosen to be neutral so that the
    engine can operate without explicit initialisation.
    """

    # Current maneuver identifier (e.g. "retract_uterus").
    current_maneuver: str = ""
    execution_phase: str = ""
    active_instrument: str = ""
    force_application: float = 0.0  # Newtons
    precision: float = 1.0  # 0‑1, higher is better
    tremor: float = 0.0  # magnitude of involuntary motion
    dexterity: float = 1.0  # 0‑1 skill factor
    exposure_quality: float = 1.0  # 0‑1
    visualization_quality: float = 1.0  # 0‑1
    tissue_tension: float = 0.0
    operative_stability: float = 1.0
    execution_latency: int = 0  # ticks
    cumulative_technical_fatigue: float = 0.0
    current_risk_level: float = 0.0
    execution_confidence: float = 1.0
    failed_maneuvers: Tuple[str, ...] = field(default_factory=tuple)
    successful_maneuvers: Tuple[str, ...] = field(default_factory=tuple)
    micro_error_accumulation: float = 0.0
    procedural_smoothness: float = 1.0
    instrument_transitions: int = 0
    handoff_count: int = 0
    unsafe_motion_count: int = 0
    corrective_maneuver_count: int = 0
    execution_history: Tuple[Tuple[int, str], ...] = field(default_factory=tuple)

    # ---------------------------------------------------------------------
    # Helper ``with_*`` methods – each returns a new immutable instance.
    # ---------------------------------------------------------------------
    def with_current_maneuver(self, maneuver: str) -> "TechnicalExecutionState":
        return replace(self, current_maneuver=maneuver)

    def with_execution_phase(self, phase: str) -> "TechnicalExecutionState":
        return replace(self, execution_phase=phase)

    def with_active_instrument(self, instrument: str) -> "TechnicalExecutionState":
        return replace(self, active_instrument=instrument)

    def with_force_application(self, force: float) -> "TechnicalExecutionState":
        return replace(self, force_application=force)

    def with_precision(self, precision: float) -> "TechnicalExecutionState":
        precision = max(0.0, min(1.0, precision))
        return replace(self, precision=precision)

    def with_tremor(self, tremor: float) -> "TechnicalExecutionState":
        return replace(self, tremor=tremor)

    def with_dexterity(self, dexterity: float) -> "TechnicalExecutionState":
        dexterity = max(0.0, min(1.0, dexterity))
        return replace(self, dexterity=dexterity)

    def with_exposure_quality(self, quality: float) -> "TechnicalExecutionState":
        quality = max(0.0, min(1.0, quality))
        return replace(self, exposure_quality=quality)

    def with_visualization_quality(self, quality: float) -> "TechnicalExecutionState":
        quality = max(0.0, min(1.0, quality))
        return replace(self, visualization_quality=quality)

    def with_tissue_tension(self, tension: float) -> "TechnicalExecutionState":
        return replace(self, tissue_tension=tension)

    def with_operative_stability(self, stability: float) -> "TechnicalExecutionState":
        stability = max(0.0, min(1.0, stability))
        return replace(self, operative_stability=stability)

    def with_execution_latency(self, latency: int) -> "TechnicalExecutionState":
        return replace(self, execution_latency=latency)

    def with_cumulative_technical_fatigue(self, fatigue: float) -> "TechnicalExecutionState":
        fatigue = max(0.0, min(1.0, fatigue))
        return replace(self, cumulative_technical_fatigue=fatigue)

    def with_current_risk_level(self, risk: float) -> "TechnicalExecutionState":
        risk = max(0.0, min(1.0, risk))
        return replace(self, current_risk_level=risk)

    def with_execution_confidence(self, confidence: float) -> "TechnicalExecutionState":
        confidence = max(0.0, min(1.0, confidence))
        return replace(self, execution_confidence=confidence)

    def add_failed_maneuver(self, maneuver: str) -> "TechnicalExecutionState":
        return replace(self, failed_maneuvers=self.failed_maneuvers + (maneuver,))

    def add_successful_maneuver(self, maneuver: str) -> "TechnicalExecutionState":
        return replace(self, successful_maneuvers=self.successful_maneuvers + (maneuver,))

    def with_micro_error_accumulation(self, err: float) -> "TechnicalExecutionState":
        err = max(0.0, err)
        return replace(self, micro_error_accumulation=err)

    def with_procedural_smoothness(self, smooth: float) -> "TechnicalExecutionState":
        smooth = max(0.0, min(1.0, smooth))
        return replace(self, procedural_smoothness=smooth)

    def with_instrument_transitions(self, count: int) -> "TechnicalExecutionState":
        return replace(self, instrument_transitions=count)

    def with_handoff_count(self, count: int) -> "TechnicalExecutionState":
        return replace(self, handoff_count=count)

    def with_unsafe_motion_count(self, count: int) -> "TechnicalExecutionState":
        return replace(self, unsafe_motion_count=count)

    def with_corrective_maneuver_count(self, count: int) -> "TechnicalExecutionState":
        return replace(self, corrective_maneuver_count=count)

    def add_execution_history(self, tick: int, maneuver: str) -> "TechnicalExecutionState":
        return replace(self, execution_history=self.execution_history + ((tick, maneuver),))
