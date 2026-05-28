"""Curriculum engine – recommends the next procedure for a learner.

The engine consults three sources:

1. **Skill graph** – static dependency map of procedures and the skill tags they
   teach.
2. **Mastery tracker** – per‑user mastery levels for procedures and skills.
3. **Learner profile** – the adaptive feedback layer (P20) supplies a
   ``focus_hint`` etc.; the curriculum engine can surface that as part of the
   recommendation.

The recommendation algorithm is deliberately simple and deterministic:

* Find all procedures whose prerequisites are satisfied (mastery >= threshold).
* Exclude procedures already mastered above the threshold.
* From the remaining candidates, pick the one with the lowest current
  procedure mastery (i.e. the biggest learning opportunity).
* If no candidate is unlocked, return the first procedure that is locked and
  explain which prerequisite is missing.

The output format matches the spec in the P21 description.
"""

from typing import Dict, List, Any

from .skill_graph import get_skill_graph
from .mastery_tracker import get_mastery, update_mastery, _MASTERED_THRESHOLD

# Recommendation threshold – a procedure is considered mastered when its
# mastery value reaches this level.
_RECOMMENDATION_THRESHOLD = 0.85


def _prereqs_satisfied(proc_info: Dict[str, Any], mastery: Dict[str, Any]) -> bool:
    """Return ``True`` if every prerequisite procedure has mastery >= threshold."""
    prereqs: List[str] = proc_info.get("prerequisites", [])
    proc_mastery = mastery.get("procedure_mastery", {})
    for pre in prereqs:
        if proc_mastery.get(pre, 0.0) < _RECOMMENDATION_THRESHOLD:
            return False
    return True


def _lowest_mastery_candidate(candidates: List[str], mastery: Dict[str, Any]) -> str | None:
    """From *candidates* return the procedure ID with the lowest mastery value.
    If none are present ``None`` is returned.
    """
    if not candidates:
        return None
    proc_mastery = mastery.get("procedure_mastery", {})
    # Default missing mastery to 0.0
    return min(candidates, key=lambda pid: proc_mastery.get(pid, 0.0))


def recommend_next_procedure(user_id: str = "default") -> Dict[str, Any]:
    """Compute a recommendation for *user_id*.

    Returns a dictionary matching the P21 specification.
    """
    graph = get_skill_graph()
    mastery = get_mastery(user_id)

    # Determine which procedures are already mastered
    mastered = {
        pid for pid, val in mastery.get("procedure_mastery", {}).items() if val >= _RECOMMENDATION_THRESHOLD
    }

    # Identify candidates whose prerequisites are satisfied
    unlocked_candidates = []
    locked_candidates = []
    for proc_id, info in graph.items():
        if proc_id in mastered:
            continue  # already mastered, skip
        if _prereqs_satisfied(info, mastery):
            unlocked_candidates.append(proc_id)
        else:
            locked_candidates.append(proc_id)

    # Choose the best unlocked candidate (lowest mastery)
    if unlocked_candidates:
        chosen = _lowest_mastery_candidate(unlocked_candidates, mastery)
        reason = "Prerequisites satisfied – focus on improving this skill set"
        unlock_status = "available"
    else:
        # No unlocked candidates – pick the first locked one and explain missing prereq
        chosen = locked_candidates[0] if locked_candidates else None
        reason = "Prerequisites not yet met – complete required prior procedures first"
        unlock_status = "locked"

    # Gather skill tags for the chosen procedure (if any)
    skill_tags = []
    if chosen:
        skill_tags = graph[chosen].get("skill_tags", [])

    # Simple next goal – aim for mastery of the dominant skill tag
    next_goal = ""
    if skill_tags:
        # Prefer the tag with lowest current mastery
        skill_mastery = mastery.get("skill_mastery", {})
        worst_tag = min(skill_tags, key=lambda t: skill_mastery.get(t, 0.0))
        next_goal = f"Achieve higher mastery in {worst_tag}"
    else:
        next_goal = "Continue overall proficiency development"

    # Alternative procedures (same prerequisite set) – simple heuristic
    alternatives: List[str] = []
    if chosen:
        chosen_prereqs = set(graph[chosen].get("prerequisites", []))
        for pid, info in graph.items():
            if pid == chosen:
                continue
            if set(info.get("prerequisites", [])) == chosen_prereqs:
                alternatives.append(pid)
        # Limit to three alternatives max
        alternatives = alternatives[:3]

    return {
        "recommended_procedure": chosen,
        "reason": reason,
        "next_goal": next_goal,
        "unlock_status": unlock_status,
        "alternative": alternatives,
        "skill_tags": skill_tags,
    }
