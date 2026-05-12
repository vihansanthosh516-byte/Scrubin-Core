from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import copy


@dataclass
class ReplayBranch:
    id: str
    parent_id: Optional[str]
    branch_tick: int
    snapshots: List[Any] = field(default_factory=list)
    description: str = ""


class ReplayTree:
    """
    Manages multiple branching timelines of the simulation.
    """
    def __init__(self):
        self.branches: Dict[str, ReplayBranch] = {
            "main": ReplayBranch("main", None, 0, description="Main timeline")
        }
        self.active_branch_id = "main"

    def branch(self, parent_id: str, tick: int, branch_id: str, description: str = "") -> ReplayBranch:
        if parent_id not in self.branches:
            raise ValueError(f"Parent branch {parent_id} not found")
        
        new_branch = ReplayBranch(
            id=branch_id,
            parent_id=parent_id,
            branch_tick=tick,
            description=description
        )
        self.branches[branch_id] = new_branch
        return new_branch

    def get_branch(self, branch_id: str) -> Optional[ReplayBranch]:
        return self.branches.get(branch_id)


class ReplayDiffEngine:
    """
    Calculates differences between two world states or snapshots.
    """
    def diff_worlds(self, world_a: Any, world_b: Any) -> dict:
        diffs = {
            "vitals": {},
            "organs": {},
            "resources": {},
            "mortality_delta": round(world_b.mortality_risk - world_a.mortality_risk, 6)
        }
        
        # Diff vitals
        v_a = world_a.physiology.vitals
        v_b = world_b.physiology.vitals
        for key in set(v_a.keys()) | set(v_b.keys()):
            a_val = v_a.get(key, 0.0)
            b_val = v_b.get(key, 0.0)
            if abs(a_val - b_val) > 1e-6:
                diffs["vitals"][key] = {"before": round(a_val, 4), "after": round(b_val, 4), "delta": round(b_val - a_val, 4)}

        # Diff organs
        o_a = world_a.organ_state.to_dict()
        o_b = world_b.organ_state.to_dict()
        for organ in o_a:
            h_a = o_a[organ].get("health", 0.0)
            h_b = o_b[organ].get("health", 0.0)
            if abs(h_a - h_b) > 1e-6:
                diffs["organs"][organ] = {"before": round(h_a, 4), "after": round(h_b, 4), "delta": round(h_b - h_a, 4)}

        return diffs
