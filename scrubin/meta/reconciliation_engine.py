"""Deterministic reconciliation of consistency violations.

The engine receives a ``SystemConsistencyReport`` and the original *state* and
produces a new state where deterministic correction rules have been applied.
No new information is generated – only existing fields may be adjusted based on
pre‑defined priority ordering.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .models import SystemConsistencyReport


class ReconciliationEngine:
    """Resolve deterministic conflicts.

    The current implementation applies a very small rule set:
    * ``low_map`` → raise cardiovascular MAP to a safe 100 mmHg.
    * ``*_stress_high`` → clamp the offending system's ``stress_level`` to the
      threshold of 1.0.
    * All other violations are ignored (state left unchanged).
    """

    @staticmethod
    def _resolve_low_map(state: Any) -> Any:
        phys = getattr(state, "physiology", None)
        if phys is None:
            return state
        cv = getattr(phys, "cardiovascular", None)
        if cv is None:
            return state
        # deterministic correction: set MAP to 100 if it is low
        if cv.map < 80.0:
            cv = replace(cv, map=100.0)
            phys = replace(phys, cardiovascular=cv)
            # If *state* is a frozen dataclass we can use replace, otherwise create a new instance
            try:
                state = replace(state, physiology=phys)
            except Exception:
                state = type(state)(phys)
        return state

    @staticmethod
    def _clamp_stress(state: Any, system_name: str) -> Any:
        phys = getattr(state, "physiology", None)
        if phys is None:
            return state
        sys = getattr(phys, system_name, None)
        if sys is None:
            return state
        if getattr(sys, "stress_level", 0.0) > 1.0:
            sys = replace(sys, stress_level=1.0)
            phys = replace(phys, **{system_name: sys})
            try:
                state = replace(state, physiology=phys)
            except Exception:
                state = type(state)(phys)
        return state

    @staticmethod
    def resolve(report: SystemConsistencyReport, state: Any) -> Any:
        """Deterministically resolve *report* against *state* and return a new state.

        The function applies the deterministic rules in a fixed order, guaranteeing
        that the same set of violations always results in the same corrected
        state.
        """
        new_state = state
        # Apply low‑map correction first
        if "low_map" in report.violations:
            new_state = ReconciliationEngine._resolve_low_map(new_state)
        # Clamp stress for any system that reported a stress‑high violation
        for viol in report.violations:
            if viol.endswith("_stress_high"):
                sys_name = viol.replace("_stress_high", "")
                new_state = ReconciliationEngine._clamp_stress(new_state, sys_name)
        return new_state
