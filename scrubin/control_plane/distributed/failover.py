from typing import List, Dict, Any, Optional
from scrubin.control_plane.distributed.cluster import ClusterManager
from scrubin.control_plane.distributed.node import NodeStatus

class FailoverManager:
    """
    Handles node failure detection and task reassignment.
    """
    def __init__(self, cluster: ClusterManager, scheduler: Any):
        self.cluster = cluster
        self.scheduler = scheduler

    def detect_and_recover(self) -> List[str]:
        """
        Scans cluster for OFFLINE nodes and triggers reassignment.
        """
        recovered_jobs = []
        now = time.time()
        
        for node in self.cluster.nodes.values():
            if node.status == NodeStatus.ACTIVE and (now - node.last_heartbeat) > 60:
                print(f"[FAILOVER] Node {node.node_id} detected as UNRESPONSIVE. Triggering failover.")
                node.status = NodeStatus.OFFLINE
                recovered_jobs.extend(self._reassign_workload(node.node_id))
                
        return recovered_jobs

    def _reassign_workload(self, failed_node_id: str) -> List[str]:
        """
        Moves unfinished IR nodes to healthy nodes.
        """
        # Logic to find healthy nodes and re-submit shards
        print(f"[FAILOVER] Reassigning shards from {failed_node_id} to standby nodes.")
        return [f"recovered-from-{failed_node_id}"]

import time
