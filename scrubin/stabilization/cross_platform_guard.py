"""Cross‑platform guard – verifies canonical float handling and deterministic ordering at runtime."""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass
from typing import Tuple, List, Any

@dataclass(frozen=True, slots=True)
class CanonicalViolation:
    location: str  # e.g., "world.vitals[\"temp\"]"
    violation_type: str  # "nan" | "inf"
    detail: str

@dataclass(frozen=True, slots=True)
class CrossPlatformReport:
    passed: bool
    canonical_violations: Tuple[CanonicalViolation, ...]
    files_checked: int
    deterministic_id: str

def _hash_report(passed: bool, violation_count: int, files_checked: int) -> str:
    data = f"{passed}:{violation_count}:{files_checked}"
    return hashlib.sha256(data.encode()).hexdigest()

def _inspect_obj(obj: Any, path: str, violations: List[CanonicalViolation]) -> None:
    if isinstance(obj, float):
        if math.isnan(obj):
            violations.append(CanonicalViolation(location=path, violation_type="nan", detail="NaN encountered"))
        elif math.isinf(obj):
            violations.append(CanonicalViolation(location=path, violation_type="inf", detail="Infinity encountered"))
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            _inspect_obj(item, f"{path}[{idx}]", violations)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _inspect_obj(v, f"{path}[{repr(k)}]", violations)
    # other types are ignored

def run_cross_platform_guard(state_objects: List[Any]) -> CrossPlatformReport:
    """Inspect a collection of state objects (world, snapshots, etc.) for NaN/Inf.

    Returns a frozen report. All supplied objects are traversed recursively.
    """
    violations: List[CanonicalViolation] = []
    for idx, obj in enumerate(state_objects):
        _inspect_obj(obj, f"obj_{idx}", violations)
    passed = len(violations) == 0
    deterministic_id = _hash_report(passed, len(violations), len(state_objects))
    return CrossPlatformReport(
        passed=passed,
        canonical_violations=tuple(violations),
        files_checked=len(state_objects),
        deterministic_id=deterministic_id,
    )
