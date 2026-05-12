import time
from typing import Dict, List, Any, Optional
from scrubin.control_plane.distributed.node import ExecutionNode, NodeStatus

class ClusterManager:
    """
    Global manager for execution node health and cluster-wide resource discovery.
    """
    def __init__(self):
        self.nodes: Dict[str, ExecutionNode] = {}
        self.global_queue_size = 0
        self.last_rebalance = time.time()

    def register_node(self, node: ExecutionNode):
        print(f"[CLUSTER] Registering node {node.node_id} ({node.capabilities.latency_class})")
        self.nodes[node.node_id] = node

    def deregister_node(self, node_id: str):
        if node_id in self.nodes:
            print(f"[CLUSTER] Deregistering node {node_id}")
            del self.nodes[node_id]

    def update_heartbeat(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].last_heartbeat = time.time()

    def get_active_nodes(self) -> List[ExecutionNode]:
        # Simple timeout logic for node liveness
        now = time.time()
        return [n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE and (now - n.last_heartbeat) < 30]

    def get_cluster_health_score(self) -> float:
        active = len(self.get_active_nodes())
        total = len(self.nodes)
        return active / total if total > 0 else 0.0
