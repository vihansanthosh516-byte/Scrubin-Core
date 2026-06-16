"""Deterministic invariant checking for the meta‑layer.

The engine ensures that the supplied *state* does not contain impossible or
contradictory values across layers.  It returns a ``DeterministicInvariantCheck``
containing a sorted tuple of issue identifiers.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import DeterministicInvariantCheck


class InvariantEngine:
    """Perform deterministic invariant validation.

    Currently only inspects the physiological ``SystemsState`` for out‑of‑range
    numeric fields.  The checks are intentionally simple but fully deterministic.
    """

    @staticmethod
    def _check_physiology(state: Any) -> Tuple[str, ...]:
        issues: list[str] = []
        phys = getattr(state, "physiology", None)
        if phys is None:
            return tuple()
        cv = getattr(phys, "cardiovascular", None)
        if cv is not None:
            if not (0.0 <= cv.map <= 200.0):
                issues.append("map_out_of_bounds")
            if not (0.0 <= cv.perfusion <= 2.0):
                issues.append("cardiovascular_perfusion_out_of_bounds")
        # Generic bounds for other systems' perfusion and stress
        for name in ["respiratory", "renal", "hepatic", "neurologic", "endocrine", "immune", "metabolic"]:
            sys = getattr(phys, name, None)
            if sys is None:
                continue
            if hasattr(sys, "perfusion"):
                perf = getattr(sys, "perfusion")
                if not (0.0 <= perf <= 2.0):
                    issues.append(f"{name}_perfusion_out_of_bounds")
            if hasattr(sys, "stress_level"):
                stress = getattr(sys, "stress_level")
                if not (0.0 <= stress <= 10.0):
                    issues.append(f"{name}_stress_out_of_bounds")
        return tuple(sorted(issues))

    @staticmethod
    def check(state: Any) -> DeterministicInvariantCheck:
        """Return a deterministic ``DeterministicInvariantCheck`` for *state*.
        """
        issues = InvariantEngine._check_physiology(state)
        return DeterministicInvariantCheck(issues=issues)
