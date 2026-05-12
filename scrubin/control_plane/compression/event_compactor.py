from typing import List, Dict, Any
import json

class EventCompactor:
    """
    Compresses execution history using semantic delta and importance strategies.
    """
    def __init__(self, importance_threshold: float = 0.5):
        self.threshold = importance_threshold
        self.last_state: Dict[str, Any] = {}

    def compact_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted = []
        for ev in events:
            # 1. Delta Compression
            payload = ev.get("payload", {})
            delta = self._calculate_delta(payload)
            
            if delta or self._is_critical(ev):
                ev["payload"] = delta if delta else payload
                compacted.append(ev)
                self.last_state.update(payload)
                
        return compacted

    def _calculate_delta(self, current: Dict[str, Any]) -> Dict[str, Any]:
        delta = {}
        for k, v in current.items():
            if self.last_state.get(k) != v:
                delta[k] = v
        return delta

    def _is_critical(self, event: Dict[str, Any]) -> bool:
        # Clinical mortality and contract violations are never discarded
        topic = event.get("topic", "")
        if "mortality" in topic or "violation" in topic:
            return True
        return False
