from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class SystemLock:
    """
    Frozen manifest of the entire ScrubIn execution stack.
    Any drift in these versions constitutes a 'New World' and invalidates prior audits.
    """
    kernel_version: str
    replay_engine: str
    causal_graph_rules: str
    calibration_models: str

# CURRENT_LOCK = SystemLock(
#     kernel_version="1.4.2",
#     replay_engine="2.1.0",
#     causal_graph_rules="v12",
#     calibration_models="PHASE_14_STABLE"
# )
