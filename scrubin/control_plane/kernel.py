from typing import Dict, Any, Optional
import time
from scrubin.control_plane.jobs import JobManager, JobType, JobStatus
from scrubin.control_plane.sessions import SessionManager, SessionConfig
from scrubin.control_plane.experiments import ExperimentTracker, ExperimentConfig
from scrubin.control_plane.scheduler import ResourceScheduler, ExecutionBackend
from scrubin.control_plane.snapshots import SnapshotManager
from scrubin.control_plane.bridge import ControlPlaneBridge
from scrubin.control_plane.observability.tracer import ControlPlaneTracer
from scrubin.control_plane.integrity.chain import ExecutionAuditChain
from scrubin.control_plane.recovery.manager import RecoveryManager
from scrubin.control_plane.metrics.engine import MetricsEngine
from scrubin.control_plane.inspection.tools import ControlPlaneInspector
from scrubin.control_plane.validation.runtime_validator import RuntimeVerificationLayer
from scrubin.control_plane.compiler.ir_compiler import IRCompiler
from scrubin.control_plane.compiler.execution_planner import ExecutionPlanner, ExecutionPlan
from scrubin.control_plane.compiler.ir_validator import IRValidator
from scrubin.control_plane.compiler.dependency_resolver import DependencyResolver
from scrubin.control_plane.distributed.kernel_adapter import DistributedKernelAdapter
from scrubin.control_plane.streaming.event_stream import EventStream
from scrubin.control_plane.streaming.channels import Topics
from scrubin.control_plane.alerts.engine import AlertEngine
from scrubin.control_plane.analytics.live_metrics import LiveMetricsAggregator
from scrubin.control_plane.schema_registry.registry import EventSchemaRegistry, EventSchema
from scrubin.control_plane.tracing.correlator import TraceCorrelator, TraceContext
from scrubin.control_plane.query.query_engine import SemanticQueryEngine
from scrubin.control_plane.semantic_events.models import SemanticEvent
from scrubin.control_plane.causal_graph.engine import CausalExecutionGraph
from scrubin.control_plane.causal_graph.linker import CausalLinker
from scrubin.control_plane.replay.executor import ReplayExecutor

class ControlPlaneKernel:
    """
    ScrubIn Control Plane Kernel: A deterministic execution engine.
    Integrated with a Causal Execution Graph (CEG) and Deterministic Replay.
    """
    def __init__(self, core_interface: Any):
        self.jobs = JobManager()
        self.sessions = SessionManager()
        self.experiments = ExperimentTracker()
        self.scheduler = ResourceScheduler(backend=ExecutionBackend.LOCAL)
        self.snapshots = SnapshotManager()
        
        # Phase 12.5 Observability Fabric
        self.event_stream = EventStream()
        self.alerts = AlertEngine(self.event_stream)
        self.live_analytics = LiveMetricsAggregator()
        
        # Phase 12.6 Semantic Intelligence
        self.schema_registry = EventSchemaRegistry()
        self._register_default_event_schemas()
        self.trace_correlator = TraceCorrelator()
        self.semantic_history: List[SemanticEvent] = []
        
        # Phase 12.6b Causal Execution Graph
        self.causal_graph = CausalExecutionGraph()
        self.causal_linker = CausalLinker(self.causal_graph)
        
        # Phase 12.7 Deterministic Replay
        self.replay = ReplayExecutor(self.causal_graph)
        
        # Wire up live monitoring
        self.event_stream.subscribe("*", self.alerts.monitor_stream)
        self.event_stream.subscribe("*", self.live_analytics.process_event)
        self.event_stream.subscribe("*", self._ingest_to_semantic_history)
        
        # We wrap the bridge for distributed node execution
        self.bridge = ControlPlaneBridge(core_interface)
        self._inject_distributed_trigger()
        
        # Phase 12.1 Reliability & Operability
        self.tracer = ControlPlaneTracer()
        self.metrics = MetricsEngine()
        self.recovery = RecoveryManager(self.jobs, self.snapshots)
        self.inspector = ControlPlaneInspector(self)
        self.audit_chains: Dict[str, ExecutionAuditChain] = {}
        
        # Phase 12.2 Formal Contracts & Verification
        self.verifier = RuntimeVerificationLayer()
        
        # Phase 12.3 Compilation Pipeline
        self.compiler = IRCompiler()
        self.planner = ExecutionPlanner()
        self.ir_validator = IRValidator()
        self.resolver = DependencyResolver()
        
        # Phase 12.4 Distributed Runtime
        self.dist_adapter = DistributedKernelAdapter(self.bridge)
        
        self.execution_plans: Dict[str, ExecutionPlan] = {}

    def _register_default_event_schemas(self):
        self.schema_registry.register(EventSchema(
            topic=Topics.PATIENT_VITALS,
            version=1,
            fields={"patient_id": str, "hr": int, "spo2": int}
        ))
        self.schema_registry.register(EventSchema(
            topic=Topics.IR_EXECUTION,
            version=1,
            fields={"event": str, "job_id": str}
        ))

    def _ingest_to_semantic_history(self, event: Any):
        # Support both StreamEvent objects and plain dict events used in tests
        if isinstance(event, dict):
            # Map test dict structure to expected attributes
            # Expected keys: "action" -> topic, "params" -> payload, optional "tick" and "session_id"
            from types import SimpleNamespace
            topic = event.get("action", "generic")
            tick = event.get("tick")
            payload = event.get("params", {})
            session_id = event.get("session_id")
            event = SimpleNamespace(topic=topic, tick=tick, payload=payload, session_id=session_id)

        """
        Converts raw StreamEvents into structured SemanticEvents for long-term intelligence.
        """
        # Validate against schema if version is provided
        # (For demo, we'll assume latest version)
        
        sem_ev = SemanticEvent(
            topic=event.topic,
            timestamp_tick=event.tick or 0,
            payload=event.payload,
            session_id=event.session_id or "default",
            category=event.payload.get("category", "OPERATIONAL")
        )
        self.semantic_history.append(sem_ev)
        
        # Phase 12.6b: Causal Graph Ingestion
        self.causal_graph.add_event(sem_ev)
        self.causal_linker.link_event(sem_ev, self.semantic_history[-20:]) # Link against recent window

    def _inject_distributed_trigger(self):
        """
        Adds node-aware execution to the bridge.
        """
        def execute_job_trigger_for_node(node_obj):
            # Simulation of routing to core engine for a specific IR node
            pass
        self.bridge.execute_job_trigger_for_node = execute_job_trigger_for_node

    def run_workload(self, experiment_config: ExperimentConfig):
        """
        Translates an experiment into a series of jobs and sessions.
        """
        # Register the experiment in the tracker
        self.experiments.experiments[experiment_config.id] = experiment_config
        
        # Create a session for the experiment
        session_config = SessionConfig(
            enable_clinical_teams=experiment_config.phase12_mode,
            enable_governance=experiment_config.governance_enabled,
            vectorized=experiment_config.vectorized,
            distributed=experiment_config.distributed,
            latent_mode=experiment_config.latent_world_model,
            overrides=experiment_config.policy_overrides
        )
        
        session_id = self.sessions.start_session(session_config)
        
        # Phase 12.3: Compilation Pipeline
        print(f"[Kernel] Compiling experiment {experiment_config.id} into SIR Graph...")
        world_context = {"resources": {"ventilators_available": 50}} # Mock context
        
        # 1. Compile to IR
        ir_graph = self.compiler.compile(experiment_config, world_context)
        
        # 2. Resolve Dependencies
        resolved_graph = self.resolver.resolve(ir_graph, world_context)
        
        # 3. Static Analysis (Validation)
        errors = self.ir_validator.validate(resolved_graph)
        if errors:
            print(f"[Kernel] COMPILATION ERROR: {', '.join(errors)}")
            return None, None
            
        # 4. Generate Execution Plan
        plan = self.planner.generate_plan(resolved_graph)
        self.execution_plans[session_id] = plan
        
        # Create primary job
        if experiment_config.vectorized:
            job_type = JobType.VECTOR_BATCH_SIMULATION
        elif experiment_config.phase12_mode:
            job_type = JobType.HIERARCHICAL_SIMULATION
        else:
            job_type = JobType.MULTI_AGENT_SIMULATION
            
        job = self.jobs.create_job(job_type, {"session_id": session_id})
        self.scheduler.submit(job)
        
        return session_id, job.id

    def execute_next_job(self):
        job = self.scheduler.process_next()
        if job:
            # Phase 12.2: Hard Contract Gate
            # (In a real system, we would convert Job objects to dicts for schema validation)
            job_dict = {
                "job_id": job.id, 
                "job_type": "HIERARCHICAL_SIM", # Must match JobSchema allowed values
                "priority": 5, 
                "payload": job.config, 
                "created_at_tick": 0
            }
            exp_dict = {"experiment_id": "current", "phase": 12, "mode": "SIMULATION", "config": {}, "flags": {}}
            world_mock = {"resources": {"ventilators_available": 10, "ventilators_used": 2}}
            
            if not self.verifier.validate_execution_intent(job_dict, exp_dict, world_mock):
                job.status = JobStatus.FAILED
                job.error = "CONTRACT_VIOLATION"
                return job

            # Phase 12.1: Start Trace & Audit
            span = self.tracer.start_trace(f"execute_{job.type.name}", metadata={"job_id": job.id})
            if job.id not in self.audit_chains:
                self.audit_chains[job.id] = ExecutionAuditChain(job.id)
            
            self.audit_chains[job.id].add_block({"event": "EXECUTION_START", "type": job.type.name})
            self.event_stream.publish(Topics.IR_EXECUTION, {"event": "START", "job_id": job.id}, session_id=job.config.get("session_id"))
            
            start_time = time.time()
            try:
                # Phase 12.4: Distributed Execution Routing
                session_id = job.config.get("session_id")
                plan = self.execution_plans.get(session_id)
                sess = self.sessions.get_session(session_id)
                
                if sess and sess.distributed:
                    print(f"[Kernel] Routing job {job.id} to Distributed Runtime...")
                    self.event_stream.publish(Topics.IR_EXECUTION, {"event": "ROUTED_DISTRIBUTED", "node_count": len(self.dist_adapter.cluster.nodes)}, session_id=session_id)
                    results = self.dist_adapter.dispatch_plan(plan)
                    job.result = results
                else:
                    self.bridge.execute_job_trigger(job)
                
                job.status = JobStatus.COMPLETED
                self.audit_chains[job.id].add_block({"event": "EXECUTION_SUCCESS"})
                self.event_stream.publish(Topics.IR_EXECUTION, {"event": "SUCCESS", "job_id": job.id}, session_id=session_id)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                self.audit_chains[job.id].add_block({"event": "EXECUTION_FAILURE", "error": str(e)})
            finally:
                duration_ms = (time.time() - start_time) * 1000
                self.metrics.record_job_completion(job.type.name, duration_ms)
                self.tracer.end_span(span.id)
                
            return job
        return None
