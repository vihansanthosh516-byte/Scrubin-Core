from typing import Dict, Any

class ObservationBuilder:
    """
    Converts internal ScrubIn state into a clinical observation vector for RL.
    Ensures zero leakage of non-observable internal CEG or replay data.
    """
    def build(self, engine_state: Any) -> Dict[str, Any]:
        return {
            "vitals": getattr(engine_state, "vitals", {}),
            "resources": getattr(engine_state, "resources", {}),
            "status": getattr(engine_state, "metadata", {}).get("status", "STABLE"),
            "time": getattr(engine_state, "tick", 0)
        }
