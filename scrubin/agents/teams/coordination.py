from typing import List, Dict, Optional
from scrubin.agents.teams.roles import TeamAgent, AttendingPhysicianAgent, ResidentAgent, NurseAgent
from scrubin.communication.engine import CommunicationEngine
from scrubin.communication.models import CommunicationChannel, MessagePriority, Message
from scrubin.world.model import SimulationWorld

class TeamCoordinationEngine:
    """
    Manages the organizational cognition of a clinical team.
    """
    def __init__(self, comms_engine: CommunicationEngine):
        self.comms = comms_engine
        self.agents: Dict[str, TeamAgent] = {}
        self.hierarchy: Dict[str, str] = {} # agent_id -> supervisor_id

    def add_agent(self, agent: TeamAgent, supervisor_id: Optional[str] = None):
        self.agents[agent.agent_id] = agent
        if supervisor_id:
            self.hierarchy[agent.agent_id] = supervisor_id

    def coordinate_step(self, patient_id: str, world: SimulationWorld):
        """
        Simulate a step of team interaction.
        """
        # 1. Agents process their messages
        for agent_id, agent in self.agents.items():
            messages = self.comms.get_new_messages_for_agent(agent_id)
            for msg in messages:
                self._handle_message(agent, msg, world)

        # 2. Agents evaluate the patient and decide whether to act or communicate
        for agent_id, agent in self.agents.items():
            recs = agent.evaluate(patient_id, world)
            
            # If a resident has a high-urgency recommendation, they might escalate
            if isinstance(agent, ResidentAgent):
                for rec in recs:
                    if rec.urgency > 0.8:
                        supervisor_id = self.hierarchy.get(agent_id)
                        if supervisor_id:
                            msg = agent.communicate(
                                supervisor_id,
                                f"Urgent concern for patient {patient_id}: {rec.proposed_action}. Reason: {', '.join(rec.reasoning)}",
                                channel=CommunicationChannel.PAGER,
                                priority=MessagePriority.STAT
                            )
                            self.comms.send_message(msg)

    def _handle_message(self, agent: TeamAgent, msg: Message, world: SimulationWorld):
        # Basic message handling logic
        pass
