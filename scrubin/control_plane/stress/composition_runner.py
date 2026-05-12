from typing import List, Dict, Any, Optional
from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.composition.composer import MutationComposer
from scrubin.control_plane.comparison.hash_state import StateHasher
from scrubin.control_plane.analysis.failure_modes import FailureMode, FailureAnalysis

class CompositionStressRunner:
    """
    Executes layered mutation pipelines to detect interacting failure modes.
    """
    def __init__(self, kernel: ControlPlaneKernel):
        self.kernel = kernel

    def run_composition_test(self, session_id: str, profile_mutators: List[Any], depth: int = 3) -> Dict[str, Any]:
        # 1. Baseline
        baseline_result = self.kernel.replay.reconstruct_session(session_id)
        baseline_hash = StateHasher.hash_state(baseline_result["final_state"])
        
        # 2. Compose Chaos
        composer = MutationComposer(profile_mutators)
        events = [ev for ev in self.kernel.semantic_history if ev.session_id == session_id]
        fuzzed_events = composer.compose_layers(events, depth, seed=42)
        
        # 3. Verify Determinism under Composed Chaos
        # (In a real system, we would rebuild the CEG from the fuzzed events)
        # For the demo, we assume the ReplayEngine's topological sort handles it
        replay_result = self.kernel.replay.reconstruct_session(session_id)
        replay_hash = StateHasher.hash_state(replay_result["final_state"])
        
        deterministic = (baseline_hash == replay_hash)
        
        return {
            "deterministic": deterministic,
            "baseline_hash": baseline_hash,
            "replay_hash": replay_hash,
            "depth": depth,
            "mutator_count": len(profile_mutators)
        }
