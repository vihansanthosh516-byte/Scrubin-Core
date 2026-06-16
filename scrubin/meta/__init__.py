"""Meta‑orchestration package providing deterministic supervisory control.

Exports:
- models (dataclasses)
- ConsistencyEngine
- InvariantEngine
- ReconciliationEngine
- OrchestrationEngine
- MetaManager
"""

from .models import (
    MetaSnapshot,
    SystemConsistencyReport,
    CrossLayerValidation,
    DeterministicInvariantCheck,
    OrchestrationPlan,
    ExecutionTrace,
)
from .consistency_engine import ConsistencyEngine
from .invariant_engine import InvariantEngine
from .reconciliation_engine import ReconciliationEngine
from .orchestration_engine import OrchestrationEngine
from .meta_manager import MetaManager

__all__ = [
    "MetaSnapshot",
    "SystemConsistencyReport",
    "CrossLayerValidation",
    "DeterministicInvariantCheck",
    "OrchestrationPlan",
    "ExecutionTrace",
    "ConsistencyEngine",
    "InvariantEngine",
    "ReconciliationEngine",
    "OrchestrationEngine",
    "MetaManager",
]
