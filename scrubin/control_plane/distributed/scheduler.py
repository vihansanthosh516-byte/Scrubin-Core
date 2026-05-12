from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from scrubin.control_plane.compiler.execution_planner import ExecutionPlan
from scrubin.control_plane.ir.model import IRNode
from scrubin.control_plane.distributed.cluster import ClusterManager
from scrubin.control_plane.distributed.node import ExecutionNode

@dataclass
class NodeAssignmentPlan:
    assignments: Dict[str, str] # node_id -> List[node_id] (Wait, should be node_id -> List[IRNode_id])
    shards: Dict[str, List[IRNode]]

class DistributedScheduler:
    """
    Partitions execution plans into shards and assigns them to distributed nodes.
    """
    def __init__(self, cluster: ClusterManager):
        self.cluster = cluster

    def schedule(self, execution_plan: ExecutionPlan) -> Dict[str, List[str]]:
        """
        Maps IR nodes to physical execution nodes based on capabilities and load.
        """
        nodes = self.cluster.get_active_nodes()
        if not nodes:
            raise RuntimeError("No active nodes available in cluster")

        assignments: Dict[str, List[str]] = {node.node_id: [] for node in nodes}
        
        # Greedy assignment based on node load and specialization
        for node_obj in execution_plan.ordered_nodes:
            # 1. Score nodes for this specific node type
            best_node = self._score_and_select_node(node_obj, nodes)
            assignments[best_node.node_id].append(node_obj.id)
            best_node.current_load += 1
            
        return assignments

    def _score_and_select_node(self, ir_node: IRNode, active_nodes: List[ExecutionNode]) -> ExecutionNode:
        # Simple heuristic: Least loaded node that supports the job type
        # In a real system, would use latency class and memory budget
        available_nodes = [n for n in active_nodes if ir_node.type in n.capabilities.supported_job_types or ir_node.type in ["SNAPSHOT", "AUDIT_LOG", "VITALS_EVAL", "ORGANS_EVAL", "MCTS_DECISION", "RESOURCE_CHECK", "CONTRACT_CHECK"]]
        
        if not available_nodes:
            # Fallback to any active node if no specialist found
            available_nodes = active_nodes
            
        return min(available_nodes, key=lambda n: n.current_load)
