from enum import Enum
from dataclasses import dataclass

class ReplayGuarantee(Enum):
    STRICT_BIT_IDENTICAL = "strict_bit_identical"
    CAUSAL_CONSISTENT = "causal_consistent"
    TEMPORAL_STABLE = "temporal_stable"

@dataclass(frozen=True)
class DeterminismContract:
    """
    Centralized rules for ScrubIn deterministic execution.
    """
    # Ordering Rules
    PRIMARY_ORDER = "causal"
    SECONDARY_ORDER = "timestamp_tick"
    TIE_BREAK_ORDER = "event_id"
    
    # Guarantees
    GUARANTEE_LEVEL = ReplayGuarantee.STRICT_BIT_IDENTICAL
    
    # Allowed Zones
    ALLOW_REORDERING_IN_TRACE = True
    ALLOW_CROSS_TRACE_DETERMINISM = False # Sessions are independent
    
    @staticmethod
    def get_sort_key(event: "Any") -> tuple:
        """
        Standardized tie-breaking sort key for all replay engines.
        """
        return (event.timestamp_tick, event.event_id)
