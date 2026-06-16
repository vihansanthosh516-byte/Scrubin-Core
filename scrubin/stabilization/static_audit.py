"""Static determinism audit – scans source for prohibited nondeterministic constructs."""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List

# Prohibited regex patterns (simple string search is sufficient for our purposes)
PROHIBITED_PATTERNS = {
    "uuid.uuid4": "error",
    "uuid.uuid1": "error",
    "datetime.utcnow": "error",
    "datetime.now\(\)": "error",
    "random.random": "error",
    "random.randint": "error",
    "random.choice": "error",
    "numpy.random": "error",
    "set\([^)]*\)": "warning",  # iteration order dependent on insertion
    "dict\.keys\(\)": "warning",  # order of dict keys may be load‑bearing
    "threading.Thread": "error",
    "asyncio\.gather": "warning",
    "time.time": "error",
    "os\.urandom": "error",
    "hash\([^)]*\)": "error",
}

@dataclass(frozen=True)
class AuditViolation:
    file_path: str
    line_number: int
    pattern_matched: str
    line_content: str
    severity: str  # "error" or "warning"

@dataclass(frozen=True)
class StaticAuditReport:
    passed: bool
    violations: Tuple[AuditViolation, ...]
    files_scanned: int
    deterministic_id: str

def _hash_report(passed: bool, violations: Tuple[AuditViolation, ...], files_scanned: int) -> str:
    data = f"{passed}:{files_scanned}:{len(violations)}"
    return hashlib.sha256(data.encode()).hexdigest()

def run_static_audit(root_dir: Path = Path(__file__).resolve().parents[1]) -> StaticAuditReport:
    """Scan all ``scrubin/`` .py files (excluding test files) for prohibited patterns.

    Returns a frozen report. Errors must be zero for the audit to pass.
    """
    violations: List[AuditViolation] = []
    py_files = list(root_dir.rglob("*.py"))
    # Exclude test directories
    py_files = [p for p in py_files if "tests" not in p.parts]
    for file_path in py_files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for pattern, severity in PROHIBITED_PATTERNS.items():
                if re.search(pattern, line):
                    violations.append(
                        AuditViolation(
                            file_path=str(file_path),
                            line_number=idx,
                            pattern_matched=pattern,
                            line_content=line.rstrip("\n"),
                            severity=severity,
                        )
                    )
    violations_sorted = tuple(sorted(violations, key=lambda v: (v.file_path, v.line_number)))
    passed = all(v.severity != "error" for v in violations_sorted)
    deterministic_id = _hash_report(passed, violations_sorted, len(py_files))
    return StaticAuditReport(
        passed=passed,
        violations=violations_sorted,
        files_scanned=len(py_files),
        deterministic_id=deterministic_id,
    )
