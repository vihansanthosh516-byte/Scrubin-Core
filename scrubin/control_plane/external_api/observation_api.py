from typing import Dict, Any
from scrubin.control_plane.external_api.safety_boundary import SafetyBoundary

class ObservationAPI:
    """
    External-facing observation interface.
    Returns only sanitized aggregate clinical state.
    """
    def __init__(self):
        self.boundary = SafetyBoundary()

    def query(self, raw_state: Dict[str, Any]) -> Dict[str, Any]:
        # Build public-safe observation
        public = {
            "hospital_load": raw_state.get("hospital_load"),
            "mortality_velocity": raw_state.get("mortality_velocity"),
            "policy_effect": raw_state.get("policy_effect"),
        }
        return self.boundary.sanitize_response(public)
