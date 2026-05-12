from typing import Dict, Any, Optional
import hashlib, json

class ReplayAccelerator:
    """
    Makes CES replay faster than real-time execution via caching,
    batch skipping, and DAG pruning.
    """
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _instruction_hash(self, ces_id: str, state_hash: str) -> str:
        raw = f"{ces_id}:{state_hash}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def lookup(self, ces_id: str, state_hash: str) -> Optional[Any]:
        key = self._instruction_hash(ces_id, state_hash)
        if key in self._cache:
            self.cache_hits += 1
            return self._cache[key]
        self.cache_misses += 1
        return None

    def store(self, ces_id: str, state_hash: str, result: Any):
        key = self._instruction_hash(ces_id, state_hash)
        self._cache[key] = result

    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
