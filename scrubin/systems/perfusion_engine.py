"""Deterministic perfusion engine.

Computes organ‑specific perfusion values from the cardiovascular haemodynamic
parameters.  All calculations are pure arithmetic; the result is a new
immutable ``SystemsState`` via ``replace``.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState, CardiovascularSystem


class PerfusionEngine:
    """Calculate deterministic organ perfusion based on cardiovascular parameters.

    The formulas are linear and deterministic – they do not involve any random
    component or external lookup.  The same input snapshot always yields the
    same output snapshot.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        cv: CardiovascularSystem = state.cardiovascular
        # Deterministic scaling factor derived from MAP, blood loss and vasopressor.
        factor = (cv.map / 100.0) * (1.0 - cv.blood_loss * 0.001) * (1.0 + cv.vasopressor_support * 0.1)
        # Ensure factor stays within a reasonable deterministic range.
        factor = max(0.0, min(2.0, factor))

        # Apply factor to each organ's perfusion (excluding the heart itself which
        # already tracks its own perfusion).
        renal = replace(state.renal, perfusion=state.renal.perfusion * factor)
        hepatic = replace(state.hepatic, perfusion=state.hepatic.perfusion * factor)
        neuro = replace(state.neurologic, perfusion=state.neurologic.perfusion * factor)
        # Respiratory perfusion is not modelled separately here; we leave it unchanged.

        return replace(
            state,
            renal=renal,
            hepatic=hepatic,
            neurologic=neuro,
        )
