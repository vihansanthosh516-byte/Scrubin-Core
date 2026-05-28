"""Learner profile model – stores a minimal per‑user learning state.

The profile lives in memory for now (no persistence). It can be
extended later with a database or external storage.
"""

from typing import Dict, Any
import copy

# Baseline profile – all values are in the range [0, 1]
_DEFAULT_PROFILE = {
    "user_id": "default",
    "skill_vector": {
        "precision": 0.5,
        "safety": 0.5,
        "speed": 0.5,
        "protocol_following": 0.5,
    },
    "procedure_history": [],
    "common_mistakes": [],
    "weak_phases": {},
}

# In‑memory store: user_id -> profile dict
_profiles: Dict[str, Dict[str, Any]] = {}


def get_profile(user_id: str = "default") -> Dict[str, Any]:
    """Return the profile for *user_id*, creating a fresh one if needed."""
    if user_id not in _profiles:
        # Deep‑copy the default so modifications do not affect the constant
        _profiles[user_id] = copy.deepcopy(_DEFAULT_PROFILE)
        _profiles[user_id]["user_id"] = user_id
    return _profiles[user_id]


def update_profile(user_id: str, run_info: Dict[str, Any]) -> Dict[str, Any]:
    """Update the learner profile given data from a completed run.

    *run_info* is expected to contain at least ``procedure_id`` and ``phase``
    from the ``complete`` payload broadcast by ``StreamManager``.
    """
    profile = get_profile(user_id)

    # Record which procedure was executed
    proc_id = run_info.get("procedure_id")
    if proc_id:
        profile["procedure_history"].append(proc_id)

    # Record the phase where the run ended – treat as a weak phase for now.
    phase = run_info.get("phase")
    if phase:
        profile["weak_phases"][phase] = profile["weak_phases"].get(phase, 0) + 1

    # Placeholder: if the run contained any violations we could record them.
    # The ``complete`` payload currently does not include violations, so we
    # keep this simple.

    # Simple skill‑vector tweak – if the run ended in a phase that has been
    # weak many times, slightly lower the related skill.
    weak_counts = profile["weak_phases"].get(phase, 0)
    if weak_counts > 3:
        # Decrease precision and safety a bit to reflect the difficulty.
        profile["skill_vector"]["precision"] = max(0.0, profile["skill_vector"]["precision"] - 0.02)
        profile["skill_vector"]["safety"] = max(0.0, profile["skill_vector"]["safety"] - 0.02)
    else:
        # Otherwise gently increase overall skill.
        profile["skill_vector"]["precision"] = min(1.0, profile["skill_vector"]["precision"] + 0.01)
        profile["skill_vector"]["safety"] = min(1.0, profile["skill_vector"]["safety"] + 0.01)

    return profile
