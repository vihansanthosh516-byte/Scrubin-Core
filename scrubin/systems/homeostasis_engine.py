"""Deterministic homeostasis engine.

The engine applies simple deterministic compensation rules based on each system's
stress level.  No randomness, no side‑effects – the result is a fresh
``SystemsState`` created with ``replace``.
"""

from __future__ import annotations

from dataclasses import replace

from .models import SystemsState, BaseSystem


def _apply_compensation(sys: BaseSystem, threshold: float = 0.5, inc: float = 0.3, max_level: float = 10.0) -> BaseSystem:
    """Increase ``compensation_level`` if ``stress_level`` exceeds *threshold*.

    The function returns a new immutable system instance via ``replace``.
    """
    if sys.stress_level > threshold:
        new_comp = min(max_level, sys.compensation_level + inc)
        return replace(sys, compensation_level=new_comp)
    return sys


class HomeostasisEngine:
    """Apply deterministic homeostatic compensation to all organ systems.

    The rule set is intentionally simple: each system raises its
    ``compensation_level`` by a fixed increment when its ``stress_level`` is
    above a deterministic threshold.
    """

    @staticmethod
    def evaluate(state: SystemsState) -> SystemsState:
        cv = _apply_compensation(state.cardiovascular)
        resp = _apply_compensation(state.respiratory)
        renal = _apply_compensation(state.renal)
        hepatic = _apply_compensation(state.hepatic)
        neuro = _apply_compensation(state.neurologic)
        endocrine = _apply_compensation(state.endocrine)
        immune = _apply_compensation(state.immune)
        metabolic = _apply_compensation(state.metabolic)

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
