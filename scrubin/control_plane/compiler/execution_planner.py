from dataclasses import dataclass, field
from typing import List, Dict, Any
from scrubin.control_plane.ir.model import IRNode, IRGraph

@dataclass
class ExecutionPlan:
    ordered_nodes: List[IRNode] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list) # List of node IDs
    resource_locks: Dict[str, str] = field(default_factory=dict) # resource_id -> job_id
    execution_boundaries: List[int] = field(default_factory=list) # tick offsets

class ExecutionPlanner:
    """
    Optimizes SIR Graphs into ordered, parallelized execution sequences.
    """
    def generate_plan(self, graph: IRGraph) -> ExecutionPlan:
        plan = ExecutionPlan()
        
        # 1. Topological Sort (Simplified for linear demo, usually involves dependency analysis)
        plan.ordered_nodes = graph.nodes
        
        # 2. Parallelization Pass (Identify independent operations)
        # Rule: VITALS_EVAL and RESOURCE_CHECK can run in parallel
        vitals_id = None
        resource_id = None
        for node in graph.nodes:
            if node.type == "VITALS_EVAL": vitals_id = node.id
            if node.type == "RESOURCE_CHECK": resource_id = node.id
            
        if vitals_id and resource_id:
            plan.parallel_groups.append([vitals_id, resource_id])
            
        # 3. Resource Locking Pass
        for node in graph.nodes:
            if node.type == "INTERVENTION":
                res_id = node.payload.get("resource_id", "GENERIC_RESOURCE")
                plan.resource_locks[res_id] = node.id
                
        # 4. Tick Boundary Mapping
        ticks = sorted(list(set(node.tick_offset for node in graph.nodes)))
        plan.execution_boundaries = ticks
        
        return plan
