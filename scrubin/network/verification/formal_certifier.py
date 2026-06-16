"""Formal Determinism Certifier – produces a deterministic certification of the network run.

The certifier aggregates execution logs, hash chain, invariant reports, and any
governance decisions to produce an immutable ``DeterminismCertificate``.  For
the lightweight implementation we simply verify that no invariant violations
or divergences exist and that the hash chain is internally consistent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Dict

from .network_invariant_engine import InvariantReport
from .replay_divergence_detector import DivergenceReport
from .hash_chain_validator import HashChainValidationReport

# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DeterminismCertificate:
    """Immutable certificate indicating deterministic correctness of a run.

    * passed – ``True`` if all checks succeed.
    * details – Human‑readable summary of checks.
    """
    passed: bool
    details: str
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        text = f"{self.passed}|{self.details}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Certifier implementation
# ---------------------------------------------------------------------------

class FormalDeterminismCertifier:
    """Generates a deterministic certificate for a completed network run.

    The ``certify`` method aggregates the provided reports and returns a
    ``DeterminismCertificate``.  In a full system this would involve exhaustive
    replay checks; here we implement a concise deterministic sanity check.
    """

    @staticmethod
    def certify(
        execution_log: List[Dict],
        network_hash_chain: List[Dict],
        invariant_report: InvariantReport,
        hash_chain_report: HashChainValidationReport,
        divergence_report: DivergenceReport,
        governance_decisions: Dict[str, str] | None = None,
    ) -> DeterminismCertificate:
        # Simple deterministic pass condition: no violations, no divergence, hash chain valid.
        passed = (
            not invariant_report.violations
            and not divergence_report.points
            and hash_chain_report.valid
        )
        details = []
        if invariant_report.violations:
            details.append(f"{len(invariant_report.violations)} invariant violations")
        if divergence_report.points:
            details.append(f"{len(divergence_report.points)} divergence points")
        if not hash_chain_report.valid:
            details.append("Hash chain validation failed")
        if passed:
            details.append("All checks passed – deterministic execution")
        else:
            details.append("Determinism check failed")
        return DeterminismCertificate(passed=passed, details="; ".join(details))
