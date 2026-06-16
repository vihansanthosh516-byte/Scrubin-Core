"""Stabilization harness – orchestrates Phase 5 stabilization suite and writes a master report.

The harness runs offline (not part of normal simulation) and exits with status 0 only when
all checks pass. The generated report is written as canonical JSON under
``scrubin/stabilization/reports/``.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import sys
from pathlib import Path
from dataclasses import dataclass

# Import sub‑modules
from scrubin.stabilization.static_audit import run_static_audit, StaticAuditReport
from scrubin.stabilization.mutation_boundary_audit import run_mutation_boundary_audit, MutationBoundaryReport
from scrubin.stabilization.store_integrity_checker import run_store_integrity_check, StoreIntegrityReport
from scrubin.stabilization.cross_platform_guard import run_cross_platform_guard, CrossPlatformReport
from scrubin.stabilization.hash_chain_validator import build_hash_chain, HashChainEntry, validate_chain
from scrubin.stabilization.replay_verifier import verify_replay, ReplayVerificationResult
from scrubin.stabilization.divergence_detector import detect_divergence, DivergenceReport
from scrubin.stabilization.mode_parity_verifier import verify_mode_parity, ParityReport

# We need a minimal world object for the runtime cross‑platform guard – a single tick
from scrubin.core.orchestrator import Orchestrator


@dataclass(frozen=True)
class StabilizationReport:
    passed: bool
    static_audit: StaticAuditReport
    mutation_audit: MutationBoundaryReport
    store_integrity: StoreIntegrityReport
    cross_platform: CrossPlatformReport
    divergence: DivergenceReport
    replay: ReplayVerificationResult
    parity: ParityReport
    total_ticks_verified: int
    phase_6_gate: bool  # True only if passed == True
    deterministic_id: str

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "static_audit": self.static_audit.__dict__,
            "mutation_audit": self.mutation_audit.__dict__,
            "store_integrity": self.store_integrity.__dict__,
            "cross_platform": self.cross_platform.__dict__,
            "divergence": self.divergence.__dict__,
            "replay": self.replay.__dict__,
            "parity": self.parity.__dict__,
            "total_ticks_verified": self.total_ticks_verified,
            "phase_6_gate": self.phase_6_gate,
            "deterministic_id": self.deterministic_id,
        }


def _hash_report(report_dict: dict) -> str:
    # canonical JSON of the top‑level report dict (sorted keys, no whitespace)
    canonical = json.dumps(report_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ScrubIn Phase 5 stabilization harness")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for all simulations")
    parser.add_argument("--ticks", type=int, default=100, help="Number of ticks to run per simulation")
    parser.add_argument("--report-dir", type=Path, default=Path(__file__).resolve().parents[1] / "reports",
                        help="Directory to write the stabilization report JSON")
    args = parser.parse_args(argv)

    # Ensure report directory exists
    args.report_dir.mkdir(parents=True, exist_ok=True)

    # 1. Static determinism audit
    static_report: StaticAuditReport = run_static_audit()

    # 2. Mutation boundary audit
    mutation_report: MutationBoundaryReport = run_mutation_boundary_audit()

    # 3. Store integrity check (stub – currently always passes)
    store_report: StoreIntegrityReport = run_store_integrity_check()

    # 4. Cross‑platform guard (runtime) – use a single‑tick world for inspection
    orch = Orchestrator(seed=args.seed, mode="autonomous")
    orch.setup()
    orch.tick()
    cp_report: CrossPlatformReport = run_cross_platform_guard([orch.world])

    # 5. Build hash chains for two scientific runs (identical seed/decisions)
    chain_a: tuple[HashChainEntry, ...] = build_hash_chain(args.seed, args.ticks, mode="autonomous")
    chain_b: tuple[HashChainEntry, ...] = build_hash_chain(args.seed, args.ticks, mode="autonomous")

    # 6. Divergence detector between the two chains
    divergence_report: DivergenceReport = detect_divergence(chain_a, chain_b)

    # 7. Replay verifier – rebuild from the event log of the first run
    replay_report: ReplayVerificationResult = verify_replay(chain_a, args.seed, args.ticks, mode="autonomous")

    # 8. Mode parity verifier – compare scientific vs benchmark world_state_hashes
    parity_report: ParityReport = verify_mode_parity(args.seed, args.ticks)

    # Overall pass condition – all sub‑reports must pass
    overall_pass = (
        static_report.passed
        and mutation_report.passed
        and store_report.passed
        and cp_report.passed
        and divergence_report.diverged is False
        and replay_report.passed
        and parity_report.passed
    )

    # Create final report object
    final_report = StabilizationReport(
        passed=overall_pass,
        static_audit=static_report,
        mutation_audit=mutation_report,
        store_integrity=store_report,
        cross_platform=cp_report,
        divergence=divergence_report,
        replay=replay_report,
        parity=parity_report,
        total_ticks_verified=args.ticks,
        phase_6_gate=overall_pass,
        deterministic_id="",  # placeholder – will be filled after conversion to dict
    )
    # Compute deterministic_id after the report dict is assembled
    report_dict = final_report.to_dict()
    det_id = _hash_report(report_dict)
    # Re‑create final report with deterministic_id set (dataclasses are frozen, so we must create a new one)
    final_report = StabilizationReport(
        passed=overall_pass,
        static_audit=static_report,
        mutation_audit=mutation_report,
        store_integrity=store_report,
        cross_platform=cp_report,
        divergence=divergence_report,
        replay=replay_report,
        parity=parity_report,
        total_ticks_verified=args.ticks,
        phase_6_gate=overall_pass,
        deterministic_id=det_id,
    )
    # Write JSON report – canonical ordering, no extra whitespace
    report_path = args.report_dir / f"stabilization_report_{args.seed}_{args.ticks}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(final_report.to_dict(), f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    return 0 if overall_pass else 1

if __name__ == "__main__":
    sys.exit(main())
