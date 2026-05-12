from typing import List, Any
from scrubin.optimization.multiagent.world.shared_kernel import SharedClinicalWorld
from scrubin.optimization.multiagent.arbitration.deterministic_resolver import DeterministicResolver
from scrubin.optimization.multiagent.causality.inter_agent_ceg import InterAgentCEG

class MultiAgentEngine:
    """
    Orchestrates the shared world tick cycle: Propose -> Resolve -> Apply -> Record.
    """
    def __init__(self, world: SharedClinicalWorld, resolver: DeterministicResolver):
        self.world = world
        self.resolver = resolver
        self.inter_ceg = InterAgentCEG()

    def tick(self, agents: List[Any]):
        # 1. Collect Proposals
        for agent in agents:
            # Agents propose actions into the world's shared buffer
            proposals = agent.propose_actions(self.world.state)
            for p in proposals:
                self.world.submit_action(agent.id, p["action"], p["priority"])

        # 2. Deterministic Arbitration
        resolved = self.resolver.resolve(self.world.pending_actions)

        # 3. Apply to Shared World
        for record in resolved:
            # In a real system, this calls world.apply(action)
            # and records inter-agent interference if resources were taken
            pass

        # 4. Cleanup and Advance
        self.world.clear_buffer()
        self.world.advance_tick()
        
        return resolved
