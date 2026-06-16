"""Deterministic consistency validation for the meta‑layer.

The implementation inspects the provided ``state`` (expected to be a
``WorldState`` or similar container) and produces a
``SystemConsistencyReport`` consisting of deterministic, sorted violation
strings.

No randomness or external data is used – the rules are pure arithmetic and
field checks.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import SystemConsistencyReport


class ConsistencyEngine:
    """Validate cross‑layer consistency.

    The *state* argument is expected to expose a ``physiology`` attribute
    containing a ``SystemsState``.  The engine checks a few simple deterministic
    constraints and returns a ``SystemConsistencyReport`` with a sorted tuple
    of violation messages.
    """

    @staticmethod
    def _check_physiology(state: Any) -> Tuple[str, ...]:
        violations: list[str] = []
        # Guard against missing attributes – treat as empty.
        phys = getattr(state, "physiology", None)
        if phys is None:
            return tuple()
        cv = getattr(phys, "cardiovascular", None)
        if cv is not None:
            if cv.map < 80.0:
                violations.append("low_map")
            if cv.stress_level > 1.0:
                violations.append("cardiovascular_stress_high")
        # Simple generic check: any system with stress > threshold
        threshold = 1.0
        for name in ["respiratory", "renal", "hepatic", "neurologic", "endocrine", "immune", "metabolic"]:
            sys = getattr(phys, name, None)
            if sys is not None and getattr(sys, "stress_level", 0.0) > threshold:
                violations.append(f"{name}_stress_high")
        return tuple(sorted(violations))

    @staticmethod
    def validate(state: Any) -> SystemConsistencyReport:
        """Return a deterministic ``SystemConsistencyReport`` for *state*.

        The report contains a sorted tuple of violation identifiers.
        """
        violations = ConsistencyEngine._check_physiology(state)
        # Additional placeholder checks could be added for knowledge/memory etc.
        return SystemConsistencyReport(violations=violations)
