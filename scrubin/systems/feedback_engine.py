"""Deterministic feedback engine.

Implements simple positive and negative feedback loops between organ systems.
All updates are performed with ``replace`` and are fully deterministic – the
same input snapshot always yields the same output snapshot.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState


class FeedbackEngine:
    """Apply deterministic feedback loops.

    * Positive feedback: high metabolic stress forces cardiovascular failure.
    * Negative feedback: once cardiovascular failure occurs, all systems receive a
      deterministic stress increase (simulating a worsening cascade).  The loop
      is bounded – stress increments are capped by the deterministic logic.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        cv = state.cardiovascular
        metabolic = state.metabolic

        # Positive feedback – metabolic stress pushes cardiovascular failure.
        if metabolic.stress_level > 5.0:
            cv = replace(cv, failure_state=True)

        # If the heart has failed, deterministic stress rise across all systems.
        if cv.failure_state:
            inc = 1.0  # deterministic increment
            cv = replace(cv, stress_level=cv.stress_level + inc)
            resp = replace(state.respiratory, stress_level=state.respiratory.stress_level + inc)
            renal = replace(state.renal, stress_level=state.renal.stress_level + inc)
            hepatic = replace(state.hepatic, stress_level=state.hepatic.stress_level + inc)
            neuro = replace(state.neurologic, stress_level=state.neurologic.stress_level + inc)
            endocrine = replace(state.endocrine, stress_level=state.endocrine.stress_level + inc)
            immune = replace(state.immune, stress_level=state.immune.stress_level + inc)
            metabolic = replace(metabolic, stress_level=metabolic.stress_level + inc)
        else:
            # No change – keep the original sub‑states.
            resp = state.respiratory
            renal = state.renal
            hepatic = state.hepatic
            neuro = state.neurologic
            endocrine = state.endocrine
            immune = state.immune

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
