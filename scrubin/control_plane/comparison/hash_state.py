import hashlib
import json
from typing import Any

class StateHasher:
    """
    Produces a deep deterministic hash of simulation states and trajectories.
    """
    @staticmethod
    def hash_state(state: Any) -> str:
        # Convert state to a sorted JSON string for stable hashing
        # In a real system, we'd handle dataclasses properly
        if hasattr(state, "__dict__"):
            data = state.__dict__
        else:
            data = state
            
        # Ensure deep sorting of dictionaries
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
