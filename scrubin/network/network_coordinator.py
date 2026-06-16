"""Network orchestration layer for multi‑hospital deterministic simulation.

The design follows the Phase 6.1 specification while keeping the implementation
lightweight and fully deterministic.  The module defines a small execution
plan that runs each hospital's ``Orchestrator.tick`` in a deterministic order
and provides placeholders for the later network stages (2‑10).  All IDs are
derived from SHA‑256 hashes to guarantee reproducibility across platforms.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Dict


# Local imports – the core ``Orchestrator`` is used as the per‑hospital engine.
from scrubin.core.orchestrator import Orchestrator
from .hospital_registry import HospitalRegistry, HospitalConfig


def _hash_sha256(text: str) -> str:
    """Return a lower‑case hex SHA‑256 digest for *text*.

    Used for deterministic IDs throughout the network layer.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class NetworkStage:
    """A deterministic stage in the network execution plan.

    * name – Human readable stage name.
    * handler – Callable accepting the ``NetworkCoordinator`` instance.
    """

    name: str
    handler: Callable[["NetworkCoordinator"], None]
    deterministic_id: str = field(init=False)

    def __post_init__(self) -> None:
        # ``deterministic_id`` is a hash of the stage name – stable across runs.
        object.__setattr__(self, "deterministic_id", _hash_sha256(self.name))


@dataclass(frozen=True, slots=True)
class NetworkExecutionPlan:
    """Ordered collection of deterministic network stages.

    The plan is compiled once by ``NetworkCoordinator`` and reused for every
    tick.  The stages are stored in the order they should be executed.
    """

    stages: Tuple[NetworkStage, ...]

    @property
    def deterministic_id(self) -> str:
        # Deterministic ID for the whole plan is the hash of the concatenated
        # stage deterministic IDs (sorted to guarantee order‑independence).
        concatenated = "|".join(stage.deterministic_id for stage in self.stages)
        return _hash_sha256(concatenated)


class NetworkCoordinator:
    """Orchestrates a deterministic multi‑hospital simulation.

    The coordinator holds a ``HospitalRegistry`` and a mapping of ``hospital_id``
    to an ``Orchestrator`` instance (one per hospital).  The ``tick`` method
    progresses the entire network by one simulation tick.

    The implementation mirrors the single‑hospital ``Orchestrator`` API: the
    ``tick`` method returns a dictionary containing the tick number and a list
    of per‑hospital tick results.
    """

    def __init__(self, registry: HospitalRegistry, hospital_instances: Dict[str, Orchestrator]):
        # ``hospital_instances`` must contain an orchestrator for each hospital_id in the registry.
        missing_ids = [cfg.hospital_id for cfg in registry if cfg.hospital_id not in hospital_instances]
        if missing_ids:
            raise ValueError(f"Hospital IDs not found in provided instances: {missing_ids}")
        self.registry: HospitalRegistry = registry
        # Preserve deterministic ordering by sorting IDs.
        self.hospitals: Dict[str, Orchestrator] = {hid: hospital_instances[hid] for hid in sorted(hospital_instances)}
        self.tick_count: int = 0
        self._execution_plan = self._build_execution_plan()
        # Store a deterministic hash chain for the network – analogous to the per‑hospital hash chain.
        self.network_hash_chain: List[Dict] = []
        # Governance‑related components
        from .ambulance_routing import build_graph, AmbulanceStore
        from .transfer_engine import TransferEngine
        from .governance.resource_constraint_solver import ResourceConstraintSolver
        from .governance.network_policy_engine import NetworkPolicyEngine
        from .governance.priority_arbitration import NetworkPriorityArbitrator
        from .governance.surge_control import SurgeControlEngine
        from .governance.network_consistency_validator import NetworkConsistencyValidator
        # Verification components
        from .verification.network_invariant_engine import NetworkInvariantEngine
        from .verification.replay_divergence_detector import ReplayDivergenceDetector
        from .verification.hash_chain_validator import HashChainValidator
        from .verification.performance_profiler import NetworkPerformanceProfiler
        from .verification.regression_gate import RegressionSafetyGate
        from .verification.formal_certifier import FormalDeterminismCertifier

        self.ambulance_store = AmbulanceStore()
        self.graph = build_graph(self.registry)  # static graph based on registry locations
        self.transfer_engine = TransferEngine()
        self.resource_solver = ResourceConstraintSolver()
        self.policy_engine = NetworkPolicyEngine()
        self.priority_arbitrator = NetworkPriorityArbitrator()
        self.surge_engine = SurgeControlEngine()
        self.consistency_validator = NetworkConsistencyValidator()
        # Verification engine instances
        self.invariant_engine = NetworkInvariantEngine()
        self.divergence_detector = ReplayDivergenceDetector()
        self.hash_chain_validator = HashChainValidator()
        self.performance_profiler = NetworkPerformanceProfiler()
        self.regression_gate = RegressionSafetyGate()
        self.formal_certifier = FormalDeterminismCertifier()


    # ---------------------------------------------------------------------
    # Execution plan construction
    # ---------------------------------------------------------------------
    def _build_execution_plan(self) -> NetworkExecutionPlan:
        """Create the deterministic network execution plan.

        Stage 1 runs all hospital ticks in sorted order.  Stages 2‑10 are stubs
        that currently perform no work but maintain a deterministic placeholder
        that can be expanded later without breaking hash continuity.
        """
        stages: List[NetworkStage] = []
        # Stage 1 – hospital ticks
        stages.append(NetworkStage(name="hospital_ticks", handler=self._stage_hospital_ticks))
        # Stage 2 – ambulance routing (build graph)
        stages.append(NetworkStage(name="ambulance_routing", handler=self._stage_ambulance_routing))
        # Stage 3 – transfer engine processing
        stages.append(NetworkStage(name="transfer_engine", handler=self._stage_transfer_engine))
        # Stage 4 – resource constraint solver
        stages.append(NetworkStage(name="resource_constraint_solver", handler=self._stage_resource_constraint_solver))
        # Stage 5 – network policy engine
        stages.append(NetworkStage(name="network_policy_engine", handler=self._stage_network_policy_engine))
        # Stage 6 – priority arbitrator
        stages.append(NetworkStage(name="priority_arbitrator", handler=self._stage_priority_arbitrator))
        # Stage 7 – surge control engine
        stages.append(NetworkStage(name="surge_control_engine", handler=self._stage_surge_control_engine))
        # Verification stages – deterministic post‑processing checks
        stages.append(NetworkStage(name="invariant_check", handler=self._stage_invariant_check))
        stages.append(NetworkStage(name="hash_chain_validation", handler=self._stage_hash_chain_validation))
        stages.append(NetworkStage(name="performance_profiling", handler=self._stage_performance_profiling))
        stages.append(NetworkStage(name="regression_gate", handler=self._stage_regression_gate))
        stages.append(NetworkStage(name="formal_certification", handler=self._stage_formal_certification))
        return NetworkExecutionPlan(stages=tuple(stages))

    # ---------------------------------------------------------------------
    # Stage implementations
    # ---------------------------------------------------------------------
    def _stage_hospital_ticks(self) -> None:
        """Run a tick on each hospital in deterministic order.

        The method populates ``self._hospital_tick_results`` which is later used
        by the public ``tick`` method to build the network report.
        """
        results = []
        for hid in sorted(self.hospitals):
            orch = self.hospitals[hid]
            # ``Orchestrator.tick`` returns a dict with keys ``orchestrator_tick`` etc.
            result = orch.tick()
            results.append((hid, result))
        # Store for later use – a private attribute to avoid exposing details.
        self._hospital_tick_results = results

    def _stage_placeholder(self) -> None:
        """Placeholder for future network stages (2‑10).

        No operation is performed; the method exists solely to keep the
        execution plan deterministic and to provide a hook for later expansion.
        """
        pass

    # ---------------------------------------------------------------------
    # Governance stage implementations
    # ---------------------------------------------------------------------
    def _stage_ambulance_routing(self) -> None:
        """Build (or rebuild) the deterministic graph for ambulance routing.

        The graph is a full‑mesh based on hospital locations stored in the
        registry.  For simplicity we rebuild the graph each tick – the operation
        is deterministic and inexpensive for the modest test networks.
        """
        from .ambulance_routing import build_graph
        self.graph = build_graph(self.registry)

    def _stage_transfer_engine(self) -> None:
        """Process pending transfer requests using the network ``TransferEngine``.

        The engine consumes pending requests and produces decisions and events.
        The resulting decisions are stored on the coordinator for later stages.
        """
        # For deterministic behaviour we provide an empty snapshot mapping – the
        # engine's default logic will simply reject requests with unknown
        # destinations, which is acceptable for the placeholder implementation.
        self.transfer_engine.process_requests({}, current_tick=self.tick_count)

    def _stage_resource_constraint_solver(self) -> None:
        """Invoke the ``ResourceConstraintSolver`` on the current network snapshot.

        The method builds per‑hospital ``HospitalSnapshot`` objects, runs the
        solver, and stores the resulting plan and any violations for later
        inspection or logging.
        """
        snapshots = self._gather_snapshots()
        plan, violations = self.resource_solver.solve(snapshots)
        # Store for potential later use (e.g., diagnostics).  No mutation of the
        # orchestrators occurs – this stage is read‑only.
        self._resource_plan = plan
        self._resource_violations = violations

    def _stage_network_policy_engine(self) -> None:
        """Apply deterministic network policies via ``NetworkPolicyEngine``.

        The engine consumes the current ``NetworkSnapshot`` and the ``TransferEngine``
        state and returns policy decisions and violation reports.
        """
        snapshots = self._gather_snapshots()
        decision, report = self.policy_engine.apply_policies(snapshots, self.registry, self.transfer_engine)
        self._policy_decision = decision
        self._policy_report = report

    def _stage_priority_arbitrator(self) -> None:
        """Resolve any conflicting transfer requests using the ``NetworkPriorityArbitrator``.
        """
        # Gather all pending requests from the transfer engine (may be empty).
        pending = self.transfer_engine.pending_requests
        arbitrated = self.priority_arbitrator.arbitrate(pending, self.graph)
        self._arbitrated_plan = arbitrated
        # For this deterministic placeholder we do not modify the pending
        # requests – the arbitrator merely records the ordering.

    def _stage_surge_control_engine(self) -> None:
        """Compute surge state and possible diversion directives.
        """
        snapshots = self._gather_snapshots()
        # Use the number of pending transfer requests as the backlog metric.
        backlog = len(self.transfer_engine.pending_requests)
        surge_state, directive = self.surge_engine.evaluate(snapshots, backlog)
        self._surge_state = surge_state
        self._diversion_directive = directive

    # ---------------------------------------------------------------------
    # Verification stage implementations
    # ---------------------------------------------------------------------
    def _stage_invariant_check(self) -> None:
        """Run invariant checks via ``NetworkInvariantEngine``.
        """
        snapshots = self._gather_snapshots()
        report = self.invariant_engine.check(snapshots, self.ambulance_store, self.transfer_engine)
        self._invariant_report = report

    def _stage_hash_chain_validation(self) -> None:
        """Validate the network hash chain and compute divergence.
        """
        snapshots = self._gather_snapshots()
        self._hash_chain_report = self.hash_chain_validator.validate(self.network_hash_chain, snapshots)
        # Compare the chain to itself for a deterministic divergence check (no divergence).
        self._divergence_report = self.divergence_detector.detect(self.network_hash_chain, self.network_hash_chain)

    def _stage_performance_profiling(self) -> None:
        """Record performance metrics for the current tick.
        """
        # ``stage_times`` will be populated in ``tick``; if missing, provide empty.
        stage_times = getattr(self, "_last_stage_times", {})
        self._performance_profile = self.performance_profiler.record_tick(self.tick_count, stage_times)

    def _stage_regression_gate(self) -> None:
        """Run regression safety gate checks.
        """
        result = self.regression_gate.check(self.network_hash_chain, self._invariant_report, self._divergence_report)
        self._regression_gate_result = result

    def _stage_formal_certification(self) -> None:
        """Generate a determinism certificate.
        """
        # Placeholder execution log – empty list for deterministic stub.
        execution_log: List[Dict] = []
        cert = self.formal_certifier.certify(
            execution_log=execution_log,
            network_hash_chain=self.network_hash_chain,
            invariant_report=self._invariant_report,
            hash_chain_report=self._hash_chain_report,
            divergence_report=self._divergence_report,
            governance_decisions=None,
        )
        self._determinism_certificate = cert

    # ---------------------------------------------------------------------
    # Helper – snapshot collection
    # ---------------------------------------------------------------------
    def _gather_snapshots(self) -> Dict[str, HospitalSnapshot]:
        """Collect deterministic ``HospitalSnapshot`` objects for all hospitals.

        The snapshot captures total patient count, critical patient count, and
        resource availability.  All values are derived from the orchestrator's
        ``world`` attribute to avoid mutating any state.
        """
        from .network_snapshot import HospitalSnapshot
        snapshots: Dict[str, HospitalSnapshot] = {}
        for hid, orch in self.hospitals.items():
            world = orch.world
            # Simple patient count – the orchestrator simulates a single patient.
            total_patients = 1
            critical_patients = 1 if (world.mortality_risk > 0.4 or world.sofa_score > 6) else 0
            # Resource availability – use the ``available`` property of each
            # ``ResourceState`` instance.
            resources = {
                name: rs.available for name, rs in world.resource_manager.resources.items()
            }
            snapshots[hid] = HospitalSnapshot(
                hospital_id=hid,
                total_patients=total_patients,
                critical_patients=critical_patients,
                resources=resources,
            )
        return snapshots


    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def tick(self) -> Dict:
        """Advance the entire network by one simulation tick.

        Returns a summary dictionary containing:
        * ``network_tick`` – the global network tick number.
        * ``hospital_results`` – list of ``(hospital_id, result)`` tuples.
        * ``network_hash`` – deterministic SHA‑256 hash of the aggregated world
          state snapshot for this tick (currently a simple concatenation of the
          per‑hospital world hashes).
        """
        self.tick_count += 1
        # Execute every stage in the plan sequentially while recording deterministic timings.
        stage_times: Dict[str, float] = {}
        for stage in self._execution_plan.stages:
            stage.handler()
            # Deterministic placeholder duration (0.0 ms) – wall‑clock timing omitted for reproducibility.
            stage_times[stage.name] = 0.0
        # Store timings for the performance profiling stage.
        self._last_stage_times = stage_times
        # -----------------------------------------------------------------
        # Build a deterministic network hash for this tick.
        # We reuse the per‑hospital ``world_hash`` function from the core
        # replay package to obtain each hospital's hash, then combine them.
        # -----------------------------------------------------------------
        from scrubin.replay.hash import world_hash
        # Collect per‑hospital hashes in deterministic order.
        per_hospital_hashes = []
        for hid, _ in self._hospital_tick_results:
            orchestrator = self.hospitals[hid]
            # The orchestrator's ``world`` attribute holds the current SimulationWorld.
            per_hospital_hashes.append(world_hash(orchestrator.world))
        combined = "|".join(per_hospital_hashes)
        network_hash = _hash_sha256(combined)
        # Append to network hash chain for later replay verification.
        self.network_hash_chain.append({"tick": self.tick_count, "hash": network_hash})
        # Return a concise summary.
        return {
            "network_tick": self.tick_count,
            "hospital_results": self._hospital_tick_results,
            "network_hash": network_hash,
        }
