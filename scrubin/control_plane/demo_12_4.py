from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.distributed.node import ExecutionNode
import time

def run_phase_12_4_demo():
    print("--- Phase 12.4: Distributed Clinical Execution & Scale-Out ---")
    
    # 1. Initialize Kernel and Register Distributed Nodes
    kernel = ControlPlaneKernel(core_interface=None)
    
    print("\n[Cluster] Initializing execution nodes...")
    node_a = ExecutionNode(node_id="worker-us-east-1")
    node_b = ExecutionNode(node_id="worker-us-west-2")
    node_c = ExecutionNode(node_id="worker-eu-central-1")
    
    kernel.dist_adapter.cluster.register_node(node_a)
    kernel.dist_adapter.cluster.register_node(node_b)
    kernel.dist_adapter.cluster.register_node(node_c)
    
    # Send heartbeats
    kernel.dist_adapter.cluster.update_heartbeat(node_a.node_id)
    kernel.dist_adapter.cluster.update_heartbeat(node_b.node_id)
    kernel.dist_adapter.cluster.update_heartbeat(node_c.node_id)
    
    # 2. Launch a Distributed Experiment
    print("\n[Orchestration] Launching distributed longitudinal experiment...")
    exp = ExperimentConfig(
        name="Global Scale Out",
        distributed=True,
        phase12_mode=True
    )
    
    session_id, job_id = kernel.run_workload(exp)
    
    # 3. Execution (Kernel dispatches to Distributed Runtime)
    print("\n[Kernel] Dispatching compiled execution plan to Distributed Runtime...")
    job = kernel.execute_next_job()
    
    print(f"\n[Distributed] Batch execution results summary:")
    for node_ir_id, status in list(job.result.items())[:5]:
        print(f"  - IR Node {node_ir_id}: {status}")
    print(f"  - Total nodes processed: {len(job.result)}")
    
    # 4. Telemetry Verification
    print("\n[Telemetry] Retrieving cluster performance data...")
    stats = kernel.dist_adapter.telemetry.get_cluster_stats()
    print(f"  - Active Scaling Nodes: {stats['active_nodes']}")
    print(f"  - Total Throughput: {stats['total_throughput']} batch operations")
    print(f"  - Avg Node Latency: {stats['avg_latency_ms']:.2f}ms")
    
    # 5. Fault Tolerance & Consistency
    print("\n[Consistency] Verifying distributed idempotency...")
    # Attempt to execute the same IR node ID again
    first_node_id = list(job.result.keys())[0]
    is_allowed = kernel.dist_adapter.consistency.verify_execution_idempotency(first_node_id)
    print(f"  - Idempotency Gate (Duplicate Node {first_node_id}): {'PASSED' if not is_allowed else 'FAILED'}")
    
    # 6. Replay Verification
    print("\n[Consistency] Validating cross-node state consensus...")
    consensus = kernel.dist_adapter.consistency.validate_cross_node_state(tick=0, state={"vitals": "STABLE"})
    print(f"  - State Consensus (Tick 0): {'VALIDATED' if consensus else 'DIVERGED'}")

    print("\n--- Phase 12.4 Distributed Execution Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_4_demo()
