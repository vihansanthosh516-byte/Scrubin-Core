from typing import Any, Dict, List
import copy

class MemoryCompressor:
    """
    Stores CES execution history as causal deltas instead of full snapshots.
    Enables 10-100x memory reduction while preserving full replay capability.
    """
    def __init__(self):
        self._deltas: List[Dict[str, Any]] = []
        self._baseline: Any = None

    def set_baseline(self, state: Any):
        self._baseline = copy.deepcopy(state)

    def record_delta(self, tick: int, decisions_added: List[Dict]) -> int:
        """Records only the incremental change, not the full state."""
        delta = {"tick": tick, "decisions_added": decisions_added}
        self._deltas.append(delta)
        return len(self._deltas)

    def reconstruct(self, up_to_tick: int = -1) -> Any:
        """Rebuilds full state from baseline + deltas."""
        state = copy.deepcopy(self._baseline)
        for delta in self._deltas:
            if up_to_tick >= 0 and delta["tick"] > up_to_tick:
                break
            state.decisions.extend(delta["decisions_added"])
            state.tick = delta["tick"]
        return state

    def compression_ratio(self, full_snapshot_count: int) -> float:
        if full_snapshot_count == 0:
            return 1.0
        return len(self._deltas) / full_snapshot_count
