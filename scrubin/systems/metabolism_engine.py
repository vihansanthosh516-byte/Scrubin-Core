"""Deterministic metabolism engine.

Updates the metabolic system based on current stress levels.  The calculation is
pure and deterministic – no stochastic elements are introduced.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState, MetabolicSystem


class MetabolismEngine:
    """Update metabolic demand, lactate, and acidosis deterministically.

    The engine uses simple linear relationships:
        * Oxygen consumption rises with stress.
        * Lactate accumulates proportional to stress.
        * Acidosis increases proportional to stress.
    All updates are performed with ``replace`` and the resulting state is
    immutable.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        metabolic: MetabolicSystem = state.metabolic
        # Deterministic increments based on current stress.
        oxygen_inc = metabolic.stress_level * 0.05
        lactate_inc = metabolic.stress_level * 0.1
        acidosis_inc = metabolic.stress_level * 0.02

        new_metabolic = replace(
            metabolic,
            oxygen_consumption=metabolic.oxygen_consumption + oxygen_inc,
            lactate=getattr(metabolic, "lactate", 0.0) + lactate_inc,
            acidosis=getattr(metabolic, "acidosis", 0.0) + acidosis_inc,
        )

        return replace(state, metabolic=new_metabolic)
