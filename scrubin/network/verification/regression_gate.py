"""Regression Safety Gate – ensures network runs meet safety criteria.

The gate checks that:
1. The network hash chain matches an optional baseline chain.
2. No invariant violations are present.
3. No divergence points are detected.

The result is an immutable ``RegressionGateResult`` indicating pass/fail.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Tuple, List, Optional

from .replay_divergence_detector import DivergenceReport
from .network_invariant_engine import InvariantReport

# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RegressionGateResult:
    """Immutable result of the regression safety gate.

    * passed – ``True`` if all checks succeed.
    * reasons – Tuple of textual reasons for failure (empty when passed).
    """
    passed: bool
    reasons: Tuple[str, ...]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        reason_str = "|".join(self.reasons)
        text = f"{self.passed}|{reason_str}"
        object.__setattr__(self, "deterministic_id", hashlib.sha256(text.encode()).hexdigest())


# ---------------------------------------------------------------------------
# Gate implementation
# ---------------------------------------------------------------------------

class RegressionSafetyGate:
    """Implements the safety gate logic.

    ``baseline_chain`` – optional list of hash‑chain entries representing the
    expected correct chain.  If omitted, the gate only checks for violations and
    divergence.
    """

    def __init__(self, baseline_chain: Optional[List[dict]] = None):
        self.baseline_chain = baseline_chain

    def check(
        self,
        network_hash_chain: List[dict],
        invariant_report: InvariantReport,
        divergence_report: DivergenceReport,
    ) -> RegressionGateResult:
        reasons: List[str] = []
        # 1. Invariant violations
        if invariant_report.violations:
            reasons.append(f"Invariant violations: {len(invariant_report.violations)}")
        # 2. Divergence points
        if divergence_report.points:
            reasons.append(f"Divergence points: {len(divergence_report.points)}")
        # 3. Baseline hash chain comparison
        if self.baseline_chain is not None:
            # Compare lengths and each entry's hash.
            if len(network_hash_chain) != len(self.baseline_chain):
                reasons.append("Hash chain length mismatch with baseline")
            else:
                for i, (a, b) in enumerate(zip(network_hash_chain, self.baseline_chain)):
                    if a.get("hash") != b.get("hash"):
                        reasons.append(f"Hash mismatch at tick {a.get('tick', i+1)}")
                        break
        passed = len(reasons) == 0
        return RegressionGateResult(passed=passed, reasons=tuple(reasons))
