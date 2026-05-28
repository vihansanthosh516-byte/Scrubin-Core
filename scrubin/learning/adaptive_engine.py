"""Adaptive feedback engine – combine learner profile and run context
into actionable guidance for the trainee.

The engine is deliberately lightweight: it pulls the learner profile,
updates it with the latest run (if supplied), extracts patterns, and then
produces a set of suggestions.  All values are deterministic and do not
require external services.
"""

from typing import Dict, Any

from .learner_profile import get_profile, update_profile
from .patterns import extract_patterns


def get_adaptive_feedback(user_id: str = "default", run_info: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return adaptive coaching suggestions.

    * ``user_id`` – identifier for the trainee (default ``"default"``).
    * ``run_info`` – optional dict from the ``complete`` payload; if provided,
      the learner profile is updated before generating feedback.
    """
    if run_info is not None:
        # Incorporate this run into the learner's history.
        update_profile(user_id, run_info)

    # Load (potentially updated) profile.
    profile = get_profile(user_id)

    # Extract high‑level patterns.
    patterns = extract_patterns(profile)

    # Build a simple focus hint based on the most weak phase.
    focus_hint = (
        f"Focus on improving performance during the {patterns['weak_phase']} phase."
        if patterns.get("weak_phase")
        else "Maintain current performance across all phases."
    )

    # Adjust difficulty – placeholder logic.
    difficulty_adjustment = "none"
    if patterns.get("repeated_error"):
        difficulty_adjustment = "reduce_speed"

    # Warning priority – very naive mapping.
    warning_priority = "high" if patterns.get("repeated_error") else "low"

    # Next goal – generic placeholder.
    next_goal = "Continue consistent practice and review feedback after each run."

    return {
        "focus_hint": focus_hint,
        "difficulty_adjustment": difficulty_adjustment,
        "warning_priority": warning_priority,
        "next_goal": next_goal,
    }
