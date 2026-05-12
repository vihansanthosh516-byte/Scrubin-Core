from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import JobType, JobStatus

def run_control_plane_demo():
    print("--- Phase 12: ScrubIn Control Plane v1 Integration ---")
    
    # 1. Initialize Control Plane Kernel (with a dummy core interface)
    print("\n[Control Plane] Booting kernel...")
    kernel = ControlPlaneKernel(core_interface=None)
    
    # 2. Define a Phase 12 Workload (Hierarchical + Multi-Agent + Vectorized)
    print("[Orchestration] Defining vectorized hierarchical experiment...")
    exp_config = ExperimentConfig(
        name="Vectorized Triage Study",
        phase12_mode=True,
        vectorized=True,
        governance_enabled=True,
        policy_overrides={"triage_strictness": 0.8}
    )
    
    # 3. Launch Workload
    print("[Orchestration] Launching workload...")
    session_id, job_id = kernel.run_workload(exp_config)
    print(f"  - Session ID: {session_id}")
    print(f"  - Primary Job ID: {job_id}")
    
    # 4. Check Scheduler
    print("\n[Scheduler] Checking job status...")
    job = kernel.jobs.get_job(job_id)
    print(f"  - Job Type: {job.type.name}")
    print(f"  - Initial Status: {job.status.name}")
    
    # 5. Execute Dispatch
    print("[Bridge] Dispatching job to execution backend...")
    executed_job = kernel.execute_next_job()
    print(f"  - Dispatched Job: {executed_job.id}")
    print(f"  - Current Status: {executed_job.status.name}")
    
    # 6. Snapshot Management
    print("\n[Snapshots] Capturing state snapshot...")
    snap_id = kernel.snapshots.capture(
        session_id=session_id, 
        tick=0, 
        state={"vitals": "STABLE", "mode": "VECTOR"}
    )
    print(f"  - Snapshot ID: {snap_id}")
    
    # 7. Experiment Tracking
    print("[Experiments] Verifying policy injection...")
    exp = kernel.experiments.experiments[exp_config.id]
    print(f"  - Governance Enabled: {exp.governance_enabled}")
    print(f"  - Policy Overrides: {exp.policy_overrides}")

    print("\n--- Phase 12 Integration Demo Complete ---")

if __name__ == "__main__":
    run_control_plane_demo()
