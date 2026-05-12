import time
from typing import List, Dict, Any, Optional
from scrubin.control_plane.ir.model import IRNode

class DistributedExecutor:
    """
    Local runtime for executing IR node batches on a specific node.
    """
    def __init__(self, node_id: str, bridge: Any):
        self.node_id = node_id
        self.bridge = bridge
        self.execution_history: List[Dict[str, Any]] = []

    def execute_batch(self, nodes: List[IRNode]) -> Dict[str, Any]:
        print(f"[EXECUTOR] Node {self.node_id} starting batch of {len(nodes)} nodes")
        results = {}
        
        for node in nodes:
            event = {
                "node_id": node.id,
                "type": node.type,
                "timestamp": time.time(),
                "status": "STARTED"
            }
            
            try:
                # Trigger the actual core bridge
                # (In distributed, this would involve a network RPC)
                self.bridge.execute_job_trigger_for_node(node)
                event["status"] = "COMPLETED"
            except Exception as e:
                event["status"] = "FAILED"
                event["error"] = str(e)
                
            self.execution_history.append(event)
            results[node.id] = event["status"]
            
        return results

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "processed_nodes": len(self.execution_history),
            "success_rate": self._calculate_success_rate()
        }

    def _calculate_success_rate(self) -> float:
        if not self.execution_history: return 1.0
        successes = [e for e in self.execution_history if e["status"] == "COMPLETED"]
        return len(successes) / len(self.execution_history)
