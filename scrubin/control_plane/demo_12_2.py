from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import JobType, JobStatus
from scrubin.control_plane.validation.runtime_validator import RuntimeVerificationLayer

def run_phase_12_2_demo():
    print("--- Phase 12.2: Control Plane Formal Contracts & Verification ---")
    
    # 1. Initialize Verification Layer
    verifier = RuntimeVerificationLayer()
    
    # 2. Test Case 1: Schema Validation (Job Schema)
    print("\n[Schema] Validating malformed job payload...")
    bad_job = {"job_id": "job-123", "job_type": "INVALID_TYPE"} # Should fail schema
    is_valid = verifier.registry.validate("JobSchema", bad_job)
    print(f"  - Schema Valid: {is_valid}")
    
    # 3. Test Case 2: Contract Violation (Resource Safety)
    print("\n[Contract] Testing resource safety violation (Ventilators)...")
    overloaded_world = {
        "resources": {
            "ventilators_available": 10,
            "ventilators_used": 12 # Over capacity
        }
    }
    good_job = {"job_id": "job-1", "job_type": "HIERARCHICAL_SIM", "payload": {}}
    res = verifier.contract_validator.validate_job(good_job, overloaded_world)
    print(f"  - Contract Valid: {res.valid}")
    print(f"  - Violations: {res.violations}")
    print(f"  - Severity: {res.severity}")
    
    # 4. Test Case 3: Runtime Guard (Hard Gate)
    print("\n[Guard] Attempting to execute low-priority job on DEGRADED system...")
    verifier.guard.system_status = "DEGRADED"
    low_prio_job = {"job_id": "job-low", "job_type": "HIERARCHICAL_SIM", "priority": 3}
    allowed = verifier.validate_execution_intent(low_prio_job, {}, overloaded_world)
    print(f"  - Guard Allowed Execution: {allowed}")
    
    # 5. Test Case 4: DiffCheck (Silent Divergence)
    print("\n[DiffCheck] Detecting silent physiological divergence...")
    world_a = {"tick": 100, "vitals": {"hr": 80, "spo2": 98}}
    world_b = {"tick": 100, "vitals": {"hr": 95, "spo2": 98}} # 15 bpm drift
    
    report = verifier.diffcheck.compare_worlds(world_a, world_b)
    print(f"  - Divergence Score: {report.divergence_score}")
    print(f"  - Flagged Vitals: {report.vital_differences}")
    
    # 6. Kernel Integration Test
    print("\n[Kernel] Verifying contract gate in full orchestration loop...")
    kernel = ControlPlaneKernel(core_interface=None)
    
    # Inject a failure condition into the kernel's mock world (if it were real)
    # For demo, we'll just trigger a known violation
    exp = ExperimentConfig(name="Contract Test")
    session_id, job_id = kernel.run_workload(exp)
    
    # Force a degraded state in the kernel's guard
    kernel.verifier.guard.system_status = "DEGRADED"
    
    job = kernel.execute_next_job()
    print(f"  - Kernel Job {job_id} status after guard gate: {job.status.name}")
    print(f"  - Error Detail: {job.error}")

    print("\n--- Phase 12.2 Contracts & Verification Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_2_demo()
