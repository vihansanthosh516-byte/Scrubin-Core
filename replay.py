from dataclasses import asdict
from scrubin.core.orchestrator import Orchestrator
from scrubin.core.replay import ReplayEngine
from scrubin.analysis.causality import CausalityBuilder
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.complication import ComplicationAgent
from scrubin.agents.procedure import ComplicationSignalAgent


def main():
    orch = Orchestrator()

    sim = SimulationAgent()
    vitals = VitalsAgent()
    complication = ComplicationAgent()
    procedure = ComplicationSignalAgent()

    sim.setup(orch)
    vitals.setup(orch)
    complication.setup(orch)
    procedure.setup(orch)

    orch.setup()

    for _ in range(5):
        orch.tick()

    engine = ReplayEngine(orch.ledger)

    state = engine.rebuild_state(target_tick=3)
    print("\n--- REPLAY STATE AT TICK 3 ---")
    print(state)

    print("\n--- CAUSALITY GRAPH ---")
    ledger_data = [asdict(e) for e in orch.ledger.all()]
    builder = CausalityBuilder(ledger_data)
    graph = builder.build()

    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    for e in graph.edges[:10]:
        src = graph.nodes[e.source]
        tgt = graph.nodes[e.target]
        print(f"  [{src.type}:t{src.tick}] --({e.reason})--> [{tgt.type}:t{tgt.tick}]")


if __name__ == "__main__":
    main()
