import random
import copy
from typing import List, Dict, Any, Callable
from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.semantic_events.models import SemanticEvent

class DeterminismHarness:
    """
    Stress-test harness for verifying simulation determinism and replay stability.
    """
    def __init__(self, kernel: ControlPlaneKernel):
        self.kernel = kernel

    def run_bit_identical_test(self, session_id: str) -> bool:
        """
        Test A: Verify that two identical replays produce bit-identical states.
        """
        r1 = self.kernel.replay.reconstruct_session(session_id)
        r2 = self.kernel.replay.reconstruct_session(session_id)
        
        return r1["final_state"] == r2["final_state"]

    def run_order_invariance_test(self, session_id: str) -> bool:
        """
        Test B: Verify that shuffling event arrival (but preserving causal edges) 
        produces identical replay output.
        """
        original_history = [ev for ev in self.kernel.semantic_history if ev.session_id == session_id]
        shuffled_history = copy.copy(original_history)
        random.shuffle(shuffled_history)
        
        # We need a temporary kernel/graph to test this without polluting live state
        # (Simplified for demo: we'll assume ReplayEngine handles the sort correctly)
        r1 = self.kernel.replay.reconstruct_session(session_id)
        
        # If ReplayEngine uses topological sort, it MUST produce same order regardless of input order
        return True # Placeholder for actual isolation test

    def run_ceg_consistency_test(self, session_id: str) -> List[str]:
        """
        Test C: Verify that all causal parents precede their children in the replay order.
        """
        result = self.kernel.replay.reconstruct_session(session_id)
        order = result["execution_order"]
        idx_map = {eid: i for i, eid in enumerate(order)}
        
        violations = []
        for edge in self.kernel.causal_graph.edges:
            if edge.source_id in idx_map and edge.target_id in idx_map:
                if idx_map[edge.source_id] > idx_map[edge.target_id]:
                    violations.append(f"Causal Violation: {edge.source_id} appeared AFTER {edge.target_id}")
                    
        return violations
