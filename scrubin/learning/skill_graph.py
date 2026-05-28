"""Skill graph for curriculum progression.

Defines a directed acyclic graph of procedures where each node lists its
prerequisite procedures (by ID) and the skill tags that the procedure trains.

The graph is static – in a real system it could be loaded from a DB or a
configuration file – but for this prototype a simple hard‑coded mapping is
sufficient.
"""

from typing import Dict, List

# Example graph – only a few procedures are defined for demonstration.
# In a full deployment you would enumerate all 31 procedures.
_SKILL_GRAPH: Dict[str, Dict[str, List[str] | List[str]]] = {
    "appendectomy": {
        "prerequisites": [],
        "skill_tags": ["basic_dissection", "bleeding_control"],
    },
    "cholecystectomy": {
        "prerequisites": ["appendectomy"],
        "skill_tags": ["advanced_dissection", "duct_management"],
    },
    "hernia_repair": {
        "prerequisites": ["appendectomy"],
        "skill_tags": ["suturing_basic"],
    },
    "colon_resection": {
        "prerequisites": ["cholecystectomy", "hernia_repair"],
        "skill_tags": ["extensive_dissection", "anastomosis"],
    },
    "lobectomy": {
        "prerequisites": ["colon_resection"],
        "skill_tags": ["lung_dissection", "vascular_control"],
    },
}


def get_skill_graph() -> Dict[str, Dict[str, List[str]]]:
    """Return a shallow copy of the skill graph.

    The caller may read but must not modify the returned structure.
    """
    return {proc: {k: list(v) for k, v in data.items()} for proc, data in _SKILL_GRAPH.items()}
