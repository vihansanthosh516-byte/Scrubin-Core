"""
CI Gate 4: Counterfactual Stability
Verifies that causal attribution remains stable across identical seeds.
"""
import sys
sys.path.insert(0, ".")

from scrubin.optimization.counterfactual.delta_computer import DeltaComputer
from scrubin.optimization.counterfactual.attribution.policy_attributor import PolicyAttributor
from scrubin.control_plane.replay.state import ReplayState

class _MockAction:
    triage_threshold = 0.25

def run_gate():
    computer = DeltaComputer()
    attributor = PolicyAttributor()

    baseline = ReplayState()
    baseline.metadata["status"] = "DECEASED"
    variant = ReplayState()
    variant.metadata["status"] = "SURVIVED"

    # Run twice — must be identical
    delta_a = computer.compute_delta({"final_state": baseline}, {"final_state": variant})
    delta_b = computer.compute_delta({"final_state": baseline}, {"final_state": variant})

    assert delta_a == delta_b, "FAIL: Counterfactual delta is non-deterministic."

    scores_a = attributor.attribute_impact(delta_a, _MockAction())
    scores_b = attributor.attribute_impact(delta_b, _MockAction())

    assert scores_a == scores_b, "FAIL: Policy attribution flipped across identical inputs."

    print("[GATE 4] PASS — Counterfactual stability verified.")

if __name__ == "__main__":
    run_gate()
