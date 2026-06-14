"""PK/PD Medication Engine – Phase 5.2.

Implements a deterministic, fixed‑step Euler integration of plasma and effect‑site
concentrations for a set of drugs. All state is passed in/out explicitly – the engine
does not retain hidden mutable globals, ensuring replay‑identical behaviour.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DrugState:
    """Immutable per‑drug pharmacokinetic state.

    Attributes
    ----------
    plasma_concentration: float
        Current plasma concentration (arbitrary units).
    effect_concentration: float
        Concentration at the effect site (same units).
    cumulative_dose: float
        Total dose administered up to the current tick.
    """

    plasma_concentration: float = 0.0
    effect_concentration: float = 0.0
    cumulative_dose: float = 0.0

    def with_updates(
        self,
        plasma: float | None = None,
        effect: float | None = None,
        cumulative: float | None = None,
    ) -> "DrugState":
        """Return a new ``DrugState`` with the supplied overrides.

        ``None`` values leave the field unchanged.
        """
        return DrugState(
            plasma_concentration=self.plasma_concentration if plasma is None else plasma,
            effect_concentration=self.effect_concentration if effect is None else effect,
            cumulative_dose=self.cumulative_dose if cumulative is None else cumulative,
        )


# ---------------------------------------------------------------------------
# Helper constants – deterministic defaults for any drug
# ---------------------------------------------------------------------------

# Simple default pharmacokinetic parameters (per‑drug overrides can be supplied by the caller)
_DEFAULT_HALF_LIFE = 4.0  # in ticks – controls elimination rate via kel = ln(2)/half_life
_DEFAULT_KE0 = 0.5       # effect‑site rate constant (per tick)
_DEFAULT_VOLUME = 1.0    # volume of distribution – unitless for this simplified model


def _kel(half_life: float) -> float:
    """Elimination constant (kel) derived from half‑life.

    kel = ln(2) / half_life
    """
    return math.log(2.0) / half_life if half_life > 0 else 0.0


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class PKPDEngine:
    """Deterministic PK/PD engine.

    The engine is *stateless* – each call receives the previous drug states, a list of
    dosing events for the current tick and a physiology mapping that may contain
    ``renal_function`` and ``hepatic_function`` multipliers. The engine returns an
    updated drug‑state mapping and a list of active drug‑pair interactions.
    """

    def __init__(self) -> None:
        # No internal mutable state – all data flows through the ``update`` call.
        pass

    # ---------------------------------------------------------------------
    # Public API – deterministic integration step
    # ---------------------------------------------------------------------
    def update(
        self,
        prev_state: Dict[str, DrugState] | None,
        dosing_events: List[Dict[str, float]],
        physiology: Dict[str, float] | None = None,
    ) -> Tuple[Dict[str, DrugState], List[Tuple[str, str, float]]]:
        """Perform a single deterministic integration step.

        Parameters
        ----------
        prev_state:
            Mapping ``drug_name → DrugState`` from the previous tick. ``None`` is
            treated as an empty mapping.
        dosing_events:
            List of dicts ``{"drug": <name>, "amount": <float>}`` representing
            instantaneous bolus administrations occurring at the current tick.
        physiology:
            Optional mapping containing ``renal_function`` and ``hepatic_function``
            multipliers (default ``1.0`` when omitted).

        Returns
        -------
        Tuple
            ``(new_state, active_interactions)`` where ``new_state`` mirrors the
            input mapping but with updated concentrations, and ``active_interactions``
            is a list of ``(drug_a, drug_b, magnitude)`` for each unordered pair of
            drugs that have a non‑zero plasma concentration.
        """

        # -----------------------------------------------------------------
        # Normalise inputs
        # -----------------------------------------------------------------
        prev_state = prev_state or {}
        physiology = physiology or {}
        renal_mult = float(physiology.get("renal_function", 1.0))
        hepatic_mult = float(physiology.get("hepatic_function", 1.0))
        dose_mult = renal_mult * hepatic_mult

        # -----------------------------------------------------------------
        # Aggregate dosing per drug for the current tick
        # -----------------------------------------------------------------
        dose_by_drug: Dict[str, float] = {}
        for ev in dosing_events:
            drug = ev.get("drug")
            amount = float(ev.get("amount", 0.0)) * dose_mult
            if not drug:
                continue
            dose_by_drug[drug] = dose_by_drug.get(drug, 0.0) + amount

        # -----------------------------------------------------------------
        # Deterministic integration – fixed step Euler, dt = 1 tick
        # -----------------------------------------------------------------
        new_state: Dict[str, DrugState] = {}
        for drug in sorted(set(prev_state) | set(dose_by_drug)):
            # Pull previous values (or defaults)
            old = prev_state.get(drug, DrugState())
            dose = dose_by_drug.get(drug, 0.0)

            # Parameter defaults – in a real system these would be drug‑specific
            half_life = _DEFAULT_HALF_LIFE
            ke0 = _DEFAULT_KE0
            kel_val = _kel(half_life)

            # Euler step for plasma concentration
            # dC = (dose/Vd - kel * C) * dt ; dt = 1, Vd = 1
            plasma = old.plasma_concentration + (dose - kel_val * old.plasma_concentration)
            plasma = max(plasma, 0.0)  # non‑negative

            # Effect‑site compartment – first‑order transfer from plasma
            effect = old.effect_concentration + ke0 * (old.plasma_concentration - old.effect_concentration)
            effect = max(effect, 0.0)

            cumulative = old.cumulative_dose + dose
            new_state[drug] = DrugState(plasma_concentration=plasma, effect_concentration=effect, cumulative_dose=cumulative)

        # -----------------------------------------------------------------
        # Compute active interactions – deterministic alphabetical pairing
        # -----------------------------------------------------------------
        active_interactions: List[Tuple[str, str, float]] = []
        drugs_with_conc = [d for d, s in new_state.items() if s.plasma_concentration > 0.0]
        for i, d1 in enumerate(sorted(drugs_with_conc)):
            for d2 in sorted(drugs_with_conc)[i + 1 :]:
                # Simple deterministic magnitude – product of plasma concentrations scaled
                mag = new_state[d1].plasma_concentration * new_state[d2].plasma_concentration * 0.1
                active_interactions.append((d1, d2, mag))

        return new_state, active_interactions

    # ---------------------------------------------------------------------
    # Convenience wrapper used by the orchestrator – generate deterministic events
    # ---------------------------------------------------------------------
    def generate_events(
        self,
        world,
    ) -> List[object]:  # ``SurgicalEvent`` placeholder – we avoid importing heavy types here
        """Create deterministic ``SurgicalEvent`` objects for PK/PD updates.

        The current implementation returns an empty list because the simulator does not
        yet consume PK/PD events directly. The method exists to satisfy the Phase 5.2
        pipeline contract and can be extended without breaking determinism.
        """
        # The orchestrator may later enrich this stub to enqueue events.
        return []
