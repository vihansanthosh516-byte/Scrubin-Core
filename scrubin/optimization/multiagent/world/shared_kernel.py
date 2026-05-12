from typing import List, Dict, Any

class SharedClinicalWorld:
    """
    Shared hospital world state for multi-agent clinical simulation.
    Acts as a central repository for pending actions and global causality.
    """
    def __init__(self, base_state: Any):
        self.state = base_state
        self.pending_actions: List[Dict[str, Any]] = []
        self.tick = 0

    def submit_action(self, agent_id: str, action: Dict[str, Any], priority: int):
        """
        Agents propose actions into the shared buffer for arbitration.
        """
        self.pending_actions.append({
            "agent_id": agent_id,
            "action": action,
            "priority": priority,
            "tick": self.tick
        })

    def clear_buffer(self):
        self.pending_actions = []

    def advance_tick(self):
        self.tick += 1
