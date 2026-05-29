"""Immutable Systems Biology state model.

This module defines a hierarchy of frozen dataclasses that model a deterministic
physiologic sub‑system.  The model is intentionally simple – each field is a
scalar (float or str) and is updated via ``replace`` in the engine.  The design
mirrors the existing ``WorldState`` pattern: every sub‑object is immutable and
provides ``with_*`` helpers where convenient.

The intention is to allow the physiology engine to evolve the whole system in a
single deterministic step while still enabling unit tests to reason about the
individual components.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple

# ---------------------------------------------------------------------------
# Sub‑system state definitions – each is a frozen dataclass with sensible
# defaults.  ``replace`` is used by the engine to produce a new immutable
# instance.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InflammatoryState:
    """Global inflammatory level (0.0‑1.0).

    ``edema`` represents capillary leak caused by inflammation.
    """

    level: float = 0.0
    edema: float = 0.0

    def with_level(self, level: float) -> "InflammatoryState":
        return replace(self, level=level)

    def with_edema(self, edema: float) -> "InflammatoryState":
        return replace(self, edema=edema)


@dataclass(frozen=True)
class ImmuneActivationState:
    """Immune system activation level (0.0‑1.0)."""

    activation: float = 0.0

    def with_activation(self, activation: float) -> "ImmuneActivationState":
        return replace(self, activation=activation)


@dataclass(frozen=True)
class CoagulationState:
    """Deterministic coagulation model.

    * ``clot_level`` – amount of clot formation (0.0‑1.0).
    * ``coagulopathy_score`` – degree of coagulation impairment (0.0‑1.0).
    * ``platelet_consumption`` – relative platelet usage.
    """

    clot_level: float = 0.0
    coagulopathy_score: float = 0.0
    platelet_consumption: float = 0.0

    def with_clot(self, clot: float) -> "CoagulationState":
        return replace(self, clot_level=clot)

    def with_coagulopathy(self, score: float) -> "CoagulationState":
        return replace(self, coagulopathy_score=score)

    def with_platelet(self, consumption: float) -> "CoagulationState":
        return replace(self, platelet_consumption=consumption)


@dataclass(frozen=True)
class PerfusionDistributionState:
    """Overall perfusion fraction (0.0‑1.0)."""

    overall_perf: float = 1.0

    def with_perf(self, perf: float) -> "PerfusionDistributionState":
        return replace(self, overall_perf=perf)


@dataclass(frozen=True)
class OxygenDebtState:
    """Cumulative oxygen debt (arbitrary units)."""

    debt: float = 0.0

    def with_debt(self, debt: float) -> "OxygenDebtState":
        return replace(self, debt=debt)


@dataclass(frozen=True)
class MetabolicReserveState:
    """Remaining metabolic reserve (0.0‑1.0)."""

    reserve: float = 1.0

    def with_reserve(self, reserve: float) -> "MetabolicReserveState":
        return replace(self, reserve=reserve)


@dataclass(frozen=True)
class AcidBaseBalanceState:
    """Arterial pH, clamped to physiological limits (6.8‑7.6)."""

    pH: float = 7.4

    def with_pH(self, pH: float) -> "AcidBaseBalanceState":
        # Clamp to a realistic range to keep the model deterministic.
        return replace(self, pH=max(6.8, min(7.6, pH)))


@dataclass(frozen=True)
class TissueHealingState:
    """Healing progress (0.0‑1.0)."""

    progress: float = 0.0

    def with_progress(self, progress: float) -> "TissueHealingState":
        return replace(self, progress=max(0.0, min(1.0, progress)))


@dataclass(frozen=True)
class NecrosisProgressionState:
    """Necrosis level (0.0‑1.0)."""

    level: float = 0.0

    def with_level(self, level: float) -> "NecrosisProgressionState":
        return replace(self, level=max(0.0, min(1.0, level)))


@dataclass(frozen=True)
class OrganDysfunctionState:
    """Aggregate organ dysfunction (0.0‑1.0)."""

    dysfunction: float = 0.0

    def with_dysfunction(self, dysfunction: float) -> "OrganDysfunctionState":
        return replace(self, dysfunction=max(0.0, min(1.0, dysfunction)))


@dataclass(frozen=True)
class EndocrineStressResponseState:
    """Simple endocrine stress model.

    ``catecholamine`` – sympathetic surge (0.0‑1.0).
    ``stress_hormone`` – cortisol‐like response (0.0‑1.0).
    """

    catecholamine: float = 0.0
    stress_hormone: float = 0.0

    def with_catecholamine(self, level: float) -> "EndocrineStressResponseState":
        return replace(self, catecholamine=max(0.0, min(1.0, level)))

    def with_stress_hormone(self, level: float) -> "EndocrineStressResponseState":
        return replace(self, stress_hormone=max(0.0, min(1.0, level)))


@dataclass(frozen=True)
class SystemicShockState:
    """Deterministic shock representation.

    ``shock_type`` can be ``"none"``, ``"hypovolemic"``, ``"septic"`` or
    ``"distributive"``. ``severity`` is a float in the range 0.0‑1.0.
    """

    shock_type: str = "none"
    severity: float = 0.0

    def with_type(self, shock_type: str) -> "SystemicShockState":
        return replace(self, shock_type=shock_type)

    def with_severity(self, severity: float) -> "SystemicShockState":
        return replace(self, severity=max(0.0, min(1.0, severity)))


# ---------------------------------------------------------------------------
# Top‑level container – aggregates all sub‑systems.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SystemsBiologyState:
    inflammatory: InflammatoryState = InflammatoryState()
    immune_activation: ImmuneActivationState = ImmuneActivationState()
    coagulation: CoagulationState = CoagulationState()
    perfusion: PerfusionDistributionState = PerfusionDistributionState()
    oxygen_debt: OxygenDebtState = OxygenDebtState()
    metabolic_reserve: MetabolicReserveState = MetabolicReserveState()
    acid_base: AcidBaseBalanceState = AcidBaseBalanceState()
    tissue_healing: TissueHealingState = TissueHealingState()
    necrosis: NecrosisProgressionState = NecrosisProgressionState()
    organ_dysfunction: OrganDysfunctionState = OrganDysfunctionState()
    endocrine: EndocrineStressResponseState = EndocrineStressResponseState()
    shock: SystemicShockState = SystemicShockState()

    # No explicit ``with_*`` helpers – the engine uses ``replace`` directly.

# End of file
