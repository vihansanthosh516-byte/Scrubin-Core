"""Deterministic inter‑system interaction engine.

The engine takes a ``SystemsState`` snapshot and propagates the effect of one
system onto another using purely deterministic arithmetic.  No randomness,
no external services – just functional updates via ``replace``.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState, CardiovascularSystem


class InteractionEngine:
    """Pure deterministic interaction logic between organ systems.

    The implementation is intentionally simple – it captures the canonical chain
    described in the specification (cardiovascular → renal → metabolic → …) but
    remains fully deterministic and side‑effect free.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        """Return a new ``SystemsState`` after applying deterministic interactions.

        The rules are illustrative yet deterministic:

        * Cardiovascular perfusion scales renal perfusion.
        * Reduced renal perfusion raises metabolic stress (simulating acidosis).
        * Metabolic stress feeds back into cardiovascular stress.
        * Cardiovascular oxygen delivery influences respiratory oxygen delivery.
        * Hepatic perfusion follows cardiovascular perfusion.
        * Immune stress rises with metabolic stress.
        * Neurologic stress rises with cardiovascular stress.
        * Endocrine compensation rises with cardiovascular stress.
        """
        cv: CardiovascularSystem = state.cardiovascular

        # ---- Cardiovascular → Renal ------------------------------------------------
        new_renal_perf = state.renal.perfusion * cv.perfusion
        renal = replace(state.renal, perfusion=new_renal_perf)

        # ---- Renal → Metabolic (stress increase) ----------------------------------
        # Simple deterministic mapping: if renal perfusion below 0.5, raise stress.
        renal_deficit = max(0.0, 0.5 - new_renal_perf)
        stress_inc = renal_deficit * 2.0  # proportional increase
        metabolic = replace(state.metabolic, stress_level=state.metabolic.stress_level + stress_inc)

        # ---- Metabolic → Cardiovascular stress ------------------------------------
        cv = replace(cv, stress_level=cv.stress_level + stress_inc)

        # ---- Cardiovascular → Respiratory oxygen delivery ---------------------------
        resp = replace(
            state.respiratory,
            oxygen_delivery=state.respiratory.oxygen_delivery * cv.oxygen_delivery,
        )

        # ---- Cardiovascular → Hepatic perfusion ------------------------------------
        hepatic = replace(state.hepatic, perfusion=state.hepatic.perfusion * cv.perfusion)

        # ---- Metabolic → Immune stress --------------------------------------------
        immune = replace(state.immune, stress_level=state.immune.stress_level + stress_inc)

        # ---- Cardiovascular → Neurologic stress -----------------------------------
        neuro = replace(state.neurologic, stress_level=state.neurologic.stress_level + cv.stress_level * 0.5)

        # ---- Cardiovascular → Endocrine compensation ------------------------------
        endocrine = replace(state.endocrine, compensation_level=state.endocrine.compensation_level + cv.stress_level * 0.2)

        # Return a brand‑new immutable snapshot.
        return replace(
            state,
            cardiovascular=cv,
            respiratory=resp,
            renal=renal,
            hepatic=hepatic,
            neurologic=neuro,
            endocrine=endocrine,
            immune=immune,
            metabolic=metabolic,
        )
