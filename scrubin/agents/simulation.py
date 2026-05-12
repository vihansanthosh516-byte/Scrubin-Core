class SimulationAgent:
    def setup(self, orchestrator) -> None:
        orchestrator.register_agent("system.boot", self._on_boot)
        orchestrator.register_agent("tick", self._on_tick)

    def _on_boot(self, event) -> None:
        print(f"[SimulationAgent] boot seed={event.payload.get('seed')}")

    def _on_tick(self, event) -> None:
        print(f"[SimulationAgent] event={event.type} tick={event.payload.get('tick')}")
