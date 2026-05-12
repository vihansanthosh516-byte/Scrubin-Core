from typing import List, Dict, Any
from scrubin.optimization.multiagent.world.resource_graph import ResourceGraph

class DeterministicResolver:
    """
    The heart of 15.5: Resolves multi-agent action conflicts with zero heuristics.
    Ensures that for a given input, the resolution order is always bit-identical.
    """
    def __init__(self, resource_graph: ResourceGraph):
        self.resources = resource_graph

    def resolve(self, pending_actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. Strict Deterministic Sort: (tick, priority DESC, agent_id)
        resolved_actions = sorted(pending_actions, key=lambda a: (
            a["tick"],
            -a.get("priority", 0),
            a["agent_id"]
        ))

        # 2. Sequential Resource Allocation
        final_actions = []
        for action_record in resolved_actions:
            action = action_record["action"]
            req_resource = action.get("required_resource")
            
            if req_resource:
                if self.resources.allocate(req_resource):
                    final_actions.append(action_record)
                else:
                    # Action blocked by contention
                    pass
            else:
                # No resource required, action proceeds
                final_actions.append(action_record)
                
        return final_actions
