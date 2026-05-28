"""Pattern extraction utilities – derive simple signals from a learner profile.

For a full implementation you would analyse the run‑by‑run history,
detect repeated violations, phase‑specific weakness, skill drift, etc.
Here we provide a minimal, deterministic stub that the adaptive engine
can consume.
"""

from typing import Dict, Any


def extract_patterns(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dictionary of high‑level patterns derived from *profile*.

    - ``weak_phase`` – the phase with the highest weak‑phase count.
    - ``repeated_error`` – the most recent entry in ``common_mistakes`` (if any).
    - ``confidence`` – a dummy confidence value.
    """
    weak_phase = None
    if profile.get("weak_phases"):
        # Pick the phase with highest count
        weak_phase = max(profile["weak_phases"].items(), key=lambda kv: kv[1])[0]

    repeated_error = None
    if profile.get("common_mistakes"):
        # Use the last recorded mistake as a placeholder
        repeated_error = profile["common_mistakes"][-1]

    confidence = 0.85  # static placeholder

    return {
        "weak_phase": weak_phase,
        "repeated_error": repeated_error,
        "confidence": confidence,
    }
