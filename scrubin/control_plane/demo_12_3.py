from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import JobType
from scrubin.control_plane.compiler.ir_compiler import IRCompiler
from scrubin.control_plane.compiler.execution_planner import ExecutionPlanner

def run_phase_12_3_demo():
    print("--- Phase 12.3: SIR Intermediate Representation & Execution Compiler ---")
    
    # 1. Initialize Kernel (Compiler Pipeline)
    kernel = ControlPlaneKernel(core_interface=None)
    
    # 2. Compile an Experiment
    print("\n[Compiler] Compiling multi-agent clinical team experiment...")
    exp = ExperimentConfig(
        name="Team Coordination Study",
        phase12_mode=True,
        governance_enabled=True
    )
    
    session_id, job_id = kernel.run_workload(exp)
    plan = kernel.execution_plans.get(session_id)
    
    print(f"\n[ExecutionPlan] Optimization complete for Session {session_id}")
    print(f"  - Ordered Nodes: {len(plan.ordered_nodes)}")
    print(f"  - Node Types: {[n.type for n in plan.ordered_nodes]}")
    print(f"  - Parallel Groups: {plan.parallel_groups}")
    print(f"  - Execution Boundaries (Ticks): {plan.execution_boundaries}")
    
    # 3. Static Analysis Test (IR Validator)
    print("\n[Static Analysis] Validating IR for determinism and coverage...")
    errors = kernel.ir_validator.validate(kernel.compiler.compile(exp, {}))
    if not errors:
        print("  - SIR Graph Validated: PASSED (No nondeterminism detected)")
    
    # 4. Resource Resolution Test
    print("\n[Resolver] Resolving resource contention...")
    world_overloaded = {"resources": {"ventilators_available": 2}}
    # Simulate a scenario with 10 intubations
    resolver_test_exp = ExperimentConfig(name="Mass Casualty")
    # This would trigger the warning in DependencyResolver
    kernel.resolver.resolve(kernel.compiler.compile(resolver_test_exp, {}), world_overloaded)
    
    # 5. Kernel Execution (receiving only the ExecutionPlan)
    print("\n[Kernel] Dispatching compiled execution sequence...")
    job = kernel.execute_next_job()
    print(f"  - Job {job.id} status: {job.status.name}")

    print("\n--- Phase 12.3 Compiled Execution Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_3_demo()
