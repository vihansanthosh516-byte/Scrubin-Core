"""
CI Gate 3: Deterministic Replay Identity
Verifies: same seed → identical execution trace → identical final state hash.
"""
import sys
sys.path.insert(0, ".")

from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.comparison.hash_state import StateHasher

def run_gate():
    session = "ci-replay-gate"

    # Run A
    kernel_a = ControlPlaneKernel(core_interface=None)
    result_a = kernel_a.replay.reconstruct_session(session)
    hash_a = StateHasher.hash_state(result_a["final_state"])

    # Run B (independent kernel, same session)
    kernel_b = ControlPlaneKernel(core_interface=None)
    result_b = kernel_b.replay.reconstruct_session(session)
    hash_b = StateHasher.hash_state(result_b["final_state"])

    assert hash_a == hash_b, f"FAIL: Replay divergence detected. {hash_a} != {hash_b}"

    print("[GATE 3] PASS — Deterministic replay identity verified.")

if __name__ == "__main__":
    run_gate()
