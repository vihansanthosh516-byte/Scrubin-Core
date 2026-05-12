from typing import Any, Dict, List, Optional
from scrubin.control_plane.compiler.execution_planner import ExecutionPlan
from scrubin.control_plane.distributed.cluster import ClusterManager
from scrubin.control_plane.distributed.scheduler import DistributedScheduler
from scrubin.control_plane.distributed.executor import DistributedExecutor
from scrubin.control_plane.distributed.replication import StateReplicator
from scrubin.control_plane.distributed.failover import FailoverManager
from scrubin.control_plane.distributed.telemetry import ClusterTelemetry
from scrubin.control_plane.distributed.consistency import DistributedConsistencyEnforcer

class DistributedKernelAdapter:
    """
    Bridges the Control Plane Kernel to the Distributed Execution Layer.
    """
    def __init__(self, bridge: Any):
        self.cluster = ClusterManager()
        self.scheduler = DistributedScheduler(self.cluster)
        self.replicator = StateReplicator()
        self.failover = FailoverManager(self.cluster, self.scheduler)
        self.telemetry = ClusterTelemetry()
        self.consistency = DistributedConsistencyEnforcer()
        self.bridge = bridge # Core interface
        
        self.executors: Dict[str, DistributedExecutor] = {}

    def dispatch_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Shards the plan and dispatches to remote executors.
        """
        # 1. Schedule across nodes
        assignments = self.scheduler.schedule(plan)
        
        # 2. Replicate state for fault tolerance
        # (Assuming session_id is in plan metadata)
        session_id = plan.ordered_nodes[0].payload.get("session_id", "default_sess")
        for node_id in assignments.keys():
            self.replicator.register_replica(session_id, node_id)
            
        # 3. Execute shards
        overall_results = {}
        for node_id, node_ir_ids in assignments.items():
            if node_id not in self.executors:
                self.executors[node_id] = DistributedExecutor(node_id, self.bridge)
                
            # Filter nodes for this assignment
            assigned_nodes = [n for n in plan.ordered_nodes if n.id in node_ir_ids]
            
            # Execute
            start_time = time.time()
            res = self.executors[node_id].execute_batch(assigned_nodes)
            duration_ms = (time.time() - start_time) * 1000
            
            # Record telemetry
            self.telemetry.record_node_event(node_id, "BATCH_EXECUTION", duration_ms)
            overall_results.update(res)
            
        return overall_results

import time
