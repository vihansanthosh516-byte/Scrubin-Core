import hashlib

class CacheCoherence:
    """
    Ensures parallel CES execution never reads stale state.
    Only causal-version-consistent cache reads are allowed.
    """
    def __init__(self):
        self._version_map = {}

    def register_version(self, key: str, state_hash: str):
        self._version_map[key] = state_hash

    def is_coherent(self, key: str, state_hash: str) -> bool:
        recorded = self._version_map.get(key)
        if recorded is None:
            return True  # No prior version — first write
        return recorded == state_hash
