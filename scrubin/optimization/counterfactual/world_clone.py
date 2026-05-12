import copy
from typing import Any

class WorldCloner:
    """
    Creates deep, deterministic copies of clinical world states.
    Ensures that parallel universes start from identical bit-level snapshots.
    """
    def clone(self, kernel: Any) -> Any:
        # 1. Capture snapshot
        # (In a real system, we'd use a formalized snapshot protocol)
        cloned_kernel = copy.deepcopy(kernel)
        
        # 2. Reset internal caches/buffers while preserving state
        if hasattr(cloned_kernel, "event_stream"):
            cloned_kernel.event_stream.clear_buffer()
            
        return cloned_kernel
