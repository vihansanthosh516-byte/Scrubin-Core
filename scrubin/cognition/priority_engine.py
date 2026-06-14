"""Deterministic priority computation for executive goals.

The function combines plan score, confidence and a support factor into a
single priority value in the range ``[0, 1]``.
"""

from __future__ import annotations

from scrubin.planner.plan import Plan


def compute_priority(plan: Plan, confidence: float, support: float) -> float:
    """Compute a deterministic priority for a goal.

    * ``plan.total_score`` – raw plan score (may exceed 1). It is normalised to
      the range ``[0, 1]`` by dividing by the maximum possible score ``plan.horizon``
      (each step contributes at most ``1.0``). If ``plan.horizon`` is ``0`` the
      score component is ``0``.
    * ``confidence`` – confidence already in ``[0, 1]``.
    * ``support`` – normalised support ``[0, 1]``.

    The weighted sum uses the coefficients required by the specification and
    the final value is clamped to ``[0, 1]``.
    """
    if plan.horizon > 0:
        score_norm = plan.total_score / plan.horizon
    else:
        score_norm = 0.0
    raw = 0.45 * score_norm + 0.35 * confidence + 0.20 * support
    # Clamp to [0, 1]
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw
