from typing import Dict, Any, List

class StateDiffVisualizer:
    """
    Generates human-readable diffs of simulation state changes.
    """
    def generate_diff_view(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> str:
        lines = []
        
        # Check Vitals
        old_vitals = old_state.get("vitals", {})
        new_vitals = new_state.get("vitals", {})
        for key in set(old_vitals.keys()) | set(new_vitals.keys()):
            ov = old_vitals.get(key)
            nv = new_vitals.get(key)
            if ov != nv:
                color = "green" if (nv or 0) > (ov or 0) else "red"
                # (Actual terminal colors omitted for simplicity)
                lines.append(f"{key.upper()}: {ov} \u2192 {nv}")
                
        # Check Resources
        old_res = old_state.get("resources", {})
        new_res = new_state.get("resources", {})
        for key in set(old_res.keys()) | set(new_res.keys()):
            ov = old_res.get(key)
            nv = new_res.get(key)
            if ov != nv:
                lines.append(f"{key.upper()}: {ov} \u2192 {nv}")
                
        if not lines:
            return "NO CHANGES"
            
        return "\n".join(lines)
