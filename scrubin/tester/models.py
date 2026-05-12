from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TestFinding:
    severity: str
    message: str
    tick: int | None = None


@dataclass
class TestRun:
    seed: int
    ticks: int
    ledger_size: int
    findings: List[TestFinding]
    score: int
    metadata: Dict[str, Any] = field(default_factory=dict)
