from typing import List, Dict, Any, Optional
import hashlib
import json

class DivergenceForensics:
    """
    Detects and reconstructs the causal origin of distributed nondeterminism.
    """
    def detect_mismatch(self, node_a_state: Dict[str, Any], node_b_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        hash_a = self._hash(node_a_state)
        hash_b = self._hash(node_b_state)
        
        if hash_a != hash_b:
            return {
                "type": "STATE_DIVERGENCE",
                "diff": self._calculate_diff(node_a_state, node_b_state),
                "hash_a": hash_a,
                "hash_b": hash_b
            }
        return None

    def _hash(self, state: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def _calculate_diff(self, a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
        diffs = []
        for k in set(a.keys()) | set(b.keys()):
            if a.get(k) != b.get(k):
                diffs.append(f"{k}: {a.get(k)} vs {b.get(k)}")
        return diffs
