"""Phase scoring utilities.

Provides a pure‑function deterministic scoring based on a phase definition,
user actions for that tick, and the current simulation state.
"""

from typing import Any, Dict, List, Tuple


def _keyword_set(texts: List[str]) -> set[str]:
    """Extract a set of lower‑cased keywords from a list of strings.

    Very naive splitter – splits on whitespace and punctuation is ignored.
    """
    keywords = set()
    for txt in texts:
        for word in txt.lower().replace(",", " ").replace(";", " ").split():
            keywords.add(word)
    return keywords


def _match_actions_to_keywords(actions: List[Dict[str, Any]], keywords: set[str]) -> int:
    """Count how many action ``action`` strings intersect the keyword set."""
    matches = 0
    for act in actions:
        act_name = str(act.get("action", "")).lower()
        if act_name in keywords:
            matches += 1
    return matches


def _state_satisfies_criteria(state: Dict[str, Any], criteria: List[str]) -> Tuple[int, List[str]]:
    """Very simple check – if any word of a criterion appears in any state value.

    Returns the number of satisfied criteria and a list of unmet criteria strings.
    """
    state_blob = " ".join(str(v).lower() for v in state.values())
    satisfied = 0
    unmet = []
    for crit in criteria:
        if crit.lower() in state_blob:
            satisfied += 1
        else:
            unmet.append(crit)
    return satisfied, unmet


def score_phase(
    phase_obj: Dict[str, Any],
    action_events: List[Dict[str, Any]],
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """Score a single phase.

    Returns a dictionary with the required fields:
        - phase (name)
        - score (0‑1 float)
        - instruction_alignment (weighted)
        - risk_penalty (weighted, negative)
        - success_score (weighted)
        - violations (list of strings)
    """
    # --- Instruction alignment ---
    instructions = phase_obj.get("instructions", [])
    instr_keywords = _keyword_set(instructions)
    instr_matches = _match_actions_to_keywords(action_events, instr_keywords)
    instr_score = (instr_matches / len(action_events)) * 0.3 if action_events else 0.0

    # --- Risk penalty ---
    risk_flags = phase_obj.get("risk_flags", [])
    risk_keywords = _keyword_set(risk_flags)
    risk_matches = _match_actions_to_keywords(action_events, risk_keywords)
    risk_score = -(risk_matches / len(action_events)) * 0.5 if action_events else 0.0

    # --- Success criteria ---
    success_criteria = phase_obj.get("success_criteria", [])
    satisfied, unmet = _state_satisfies_criteria(state, success_criteria)
    success_score = (satisfied / len(success_criteria)) * 0.5 if success_criteria else 0.0

    total_score = max(0.0, min(1.0, instr_score + risk_score + success_score))

    violations: List[str] = []
    # Add any risk actions as violations
    if risk_matches:
        for ev in action_events:
            if ev.get("action", "").lower() in risk_keywords:
                violations.append(ev.get("action", ""))
    # Add unmet success criteria
    violations.extend(unmet)

    return {
        "phase": phase_obj.get("name"),
        "score": total_score,
        "instruction_alignment": instr_score,
        "risk_penalty": risk_score,
        "success_score": success_score,
        "violations": violations,
    }
