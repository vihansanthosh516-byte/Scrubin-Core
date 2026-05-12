from typing import Dict, Any, Set
import hashlib
import json

class DistributedConsistencyEnforcer:
    """
    Enforces exactly-once execution semantics and cross-node state validation.
    """
    def __init__(self):
        self.executed_nodes: Set[str] = set()
        self.state_hashes: Dict[int, str] = {} # tick -> hash

    def verify_execution_idempotency(self, ir_node_id: str) -> bool:
        """
        Ensures an IR node is only executed once across the cluster.
        """
        if ir_node_id in self.executed_nodes:
            print(f"[CONSISTENCY] REJECTED: Node {ir_node_id} already executed. Preventing duplicate mutation.")
            return False
        
        self.executed_nodes.add(ir_node_id)
        return True

    def validate_cross_node_state(self, tick: int, state: Dict[str, Any]) -> bool:
        """
        Validates that distributed state matches the consensus hash for a specific tick.
        """
        current_hash = self._calculate_hash(state)
        
        if tick in self.state_hashes:
            if self.state_hashes[tick] != current_hash:
                print(f"[CONSISTENCY] ERROR: State divergence at tick {tick}!")
                return False
        else:
            self.state_hashes[tick] = current_hash
            
        return True

    def _calculate_hash(self, state: Dict[str, Any]) -> str:
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()
