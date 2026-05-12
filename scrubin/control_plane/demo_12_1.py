from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import JobType, JobStatus
import time

def run_phase_12_1_demo():
    print("--- Phase 12.1: Control Plane Reliability & Operability ---")
    
    # 1. Initialize Kernel
    kernel = ControlPlaneKernel(core_interface=None)
    
    # 2. Run a Job with Tracing and Auditing
    print("\n[Observability] Launching job with distributed tracing...")
    exp = ExperimentConfig(name="Reliability Test", phase12_mode=True)
    session_id, job_id = kernel.run_workload(exp)
    
    # Execute Job
    job = kernel.execute_next_job()
    print(f"  - Job {job_id} executed. Status: {job.status.name}")
    
    # 3. Verify Integrity (Audit Chain)
    print("\n[Integrity] Verifying execution audit trail...")
    chain = kernel.audit_chains[job_id]
    certification = chain.get_certification()
    print(f"  - Verification Status: {certification['certification_status']}")
    print(f"  - Chain Length: {certification['blocks']} blocks")
    print(f"  - Head Hash: {certification['head_hash'][:16]}...")
    
    # 4. Check Metrics
    print("\n[Metrics] Retrieving control plane health report...")
    health = kernel.metrics.get_health_report()
    print(f"  - System Status: {health['status']}")
    print(f"  - Job Throughput: {health['throughput_jobs_per_min']} jobs/min")
    print(f"  - Avg Latency (HIERARCHICAL_SIMULATION): {health['avg_latency'].get('HIERARCHICAL_SIMULATION', 0):.2f}ms")
    
    # 5. Simulate Failure and Recovery
    print("\n[Recovery] Simulating job failure...")
    fail_job = kernel.jobs.create_job(JobType.MULTI_AGENT_SIMULATION, {"session_id": session_id})
    fail_job.status = JobStatus.FAILED
    
    # Record a manual checkpoint for demo
    kernel.recovery.record_checkpoint(fail_job.id, tick=500, snapshot_id="snap-perfect-state")
    
    recovery_plan = kernel.recovery.attempt_recovery(fail_job.id)
    print(f"  - Failure detected in job {fail_job.id}")
    print(f"  - Recovery Strategy: {recovery_plan['strategy']}")
    print(f"  - Resuming from Tick: {recovery_plan.get('resume_tick')}")
    
    # 6. Inspection
    print("\n[Inspection] Comparing snapshots for divergence...")
    kernel.snapshots.capture(session_id, 100, {"hr": 80, "spo2": 95})
    kernel.snapshots.capture(session_id, 100, {"hr": 82, "spo2": 95}) # Divergent run
    
    snaps = kernel.snapshots.list_for_session(session_id)
    comparison = kernel.inspector.compare_snapshots(snaps[0].id, snaps[1].id)
    print(f"  - Snapshots Identical: {comparison['identical']}")
    print(f"  - Divergent Vitals: {list(comparison['diffs'].keys())}")

    print("\n--- Phase 12.1 Trust & Correctness Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_1_demo()
