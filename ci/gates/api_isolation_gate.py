"""
CI Gate 5: External API Isolation
Ensures the external API cannot leak internal simulation state.
"""
import sys
sys.path.insert(0, ".")

from scrubin.control_plane.external_api.safety_boundary import SafetyBoundary

def run_gate():
    boundary = SafetyBoundary()

    # Simulate a raw internal response with forbidden fields
    raw = {
        "hospital_load": 0.85,
        "mortality_velocity": 0.01,
        "causal_graph": {"edges": [1, 2, 3]},
        "replay_snapshot": "binary_blob_xyz",
        "kernel_internal": {"memory": "0xDEADBEEF"},
        "raw_vitals": {"hr": 120, "spo2": 88},
        "node_id": "internal_node_7",
    }

    sanitized = boundary.sanitize_response(raw)

    for forbidden in SafetyBoundary.FORBIDDEN_KEYWORDS:
        assert forbidden not in sanitized, \
            f"FAIL: Forbidden key '{forbidden}' leaked through safety boundary."

    assert "hospital_load" in sanitized, "FAIL: Public key stripped incorrectly."
    assert "mortality_velocity" in sanitized, "FAIL: Public key stripped incorrectly."

    print("[GATE 5] PASS — External API isolation verified.")

if __name__ == "__main__":
    run_gate()
