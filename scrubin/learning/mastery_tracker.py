"""Mastery tracker – records per‑procedure and per‑skill mastery.

The state lives in memory for this prototype. Each user (identified by a
string user_id) has:

* ``procedure_mastery`` – mapping procedure_id → mastery float (0‑1).
* ``skill_mastery`` – mapping skill_tag → mastery float (0‑1).

Updates are incremental – a new run can raise mastery for the procedure that
was just performed and for any skill tags associated with that procedure.
"""

from typing import Dict, Any
import copy

# In‑memory store: user_id -> mastery dict
_MASTERIES: Dict[str, Dict[str, Any]] = {}

# Threshold for considering a procedure/skill mastered
_MASTERED_THRESHOLD = 0.85


def _init_user(user_id: str) -> Dict[str, Any]:
    """Create a fresh mastery record for *user_id*.

    All mastery values start at 0.0.
    """
    return {
        "procedure_mastery": {},  # proc_id -> float
        "skill_mastery": {},      # skill_tag -> float
    }


def get_mastery(user_id: str = "default") -> Dict[str, Any]:
    """Return the mastery state for *user_id* (creating if missing)."""
    if user_id not in _MASTERIES:
        _MASTERIES[user_id] = _init_user(user_id)
    # Return a deep copy to prevent accidental external mutation.
    return copy.deepcopy(_MASTERIES[user_id])


def _update_value(old: float, delta: float, rate: float = 0.1) -> float:
    """Blend *old* toward *delta* using a simple learning rate.
    Result is clipped to [0, 1]."""
    new_val = old + rate * (delta - old)
    return max(0.0, min(1.0, new_val))


def update_mastery(
    user_id: str,
    procedure_id: str | None = None,
    score: float | None = None,
    skill_tags: list[str] | None = None,
) -> Dict[str, Any]:
    """Update the mastery for *user_id*.

    * ``procedure_id`` – the ID of the procedure just completed.
    * ``score`` – numeric run score (0‑1). If omitted the procedure mastery
      will be nudged upward slightly.
    * ``skill_tags`` – list of skill tags associated with the procedure.
    """
    if user_id not in _MASTERIES:
        _MASTERIES[user_id] = _init_user(user_id)
    mastery = _MASTERIES[user_id]

    # Update procedure mastery
    if procedure_id:
        old_proc = mastery["procedure_mastery"].get(procedure_id, 0.0)
        target = score if score is not None else 0.0
        mastery["procedure_mastery"][procedure_id] = _update_value(old_proc, target)

    # Update skill mastery for each tag
    if skill_tags:
        for tag in skill_tags:
            old_skill = mastery["skill_mastery"].get(tag, 0.0)
            # Use a modest bump toward 1.0 on each exposure
            mastery["skill_mastery"][tag] = _update_value(old_skill, 1.0)

    return copy.deepcopy(mastery)
