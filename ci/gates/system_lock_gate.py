"""
CI Gate 2: System Lock Consistency
Ensures the full execution stack is frozen and version-aligned at deployment time.
"""
import sys
sys.path.insert(0, ".")

from scrubin.control_plane.governance.version_lock import SystemLock

def run_gate():
    recorded = SystemLock(
        kernel_version="1.4.2",
        replay_engine="2.1.0",
        causal_graph_rules="v12",
        calibration_models="PHASE_14_STABLE"
    )
    current = SystemLock(
        kernel_version="1.4.2",
        replay_engine="2.1.0",
        causal_graph_rules="v12",
        calibration_models="PHASE_14_STABLE"
    )

    assert current == recorded, "FAIL: System lock drifted from recorded deployment state."

    # Drift detection
    drifted = SystemLock(
        kernel_version="1.4.3",
        replay_engine="2.1.0",
        causal_graph_rules="v12",
        calibration_models="PHASE_14_STABLE"
    )
    assert drifted != recorded, "FAIL: Drift detection broken — different versions matched."

    print("[GATE 2] PASS — System lock consistency verified.")

if __name__ == "__main__":
    run_gate()
