'''Deterministic resident agent – placeholder implementation.'''\n\nfrom __future__ import annotations\n\nfrom typing import List\n\nfrom scrubin.agents.agent_base import AgentPolicy, AgentState\nfrom scrubin.events.event import SurgicalEvent\n\nclass ResidentAgent:\n    """Simple deterministic resident agent placeholder – no actions."""
    def __init__(self, agent_id: str, role: str = "resident", initial_tick: int = 0):\n        deterministic_id = AgentState.deterministic_id_from(agent_id, initial_tick, fatigue=0.0, workload=0.0)
        self.state = AgentState(
            agent_id=agent_id,
            role=role,
            fatigue=0.0,
            workload=0.0,
            current_patient_id=None,
            available=True,
            shift_tick_start=initial_tick,
            deterministic_id=deterministic_id,
        )\n        self.policy: AgentPolicy = self\n\n    def evaluate(self, world, physiology_snapshot, resource_snapshot) -> List[SurgicalEvent]:\n        return []\n