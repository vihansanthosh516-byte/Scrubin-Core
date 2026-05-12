from typing import List, Dict
from .graph import CausalityGraph, Node


COMPUTE_CONTRACTS = {
    "vitals_compute": {
        "inputs": ["tick", "complication"],
        "policy": "merge_latest_state",
        "deterministic_key": "tick+complication",
        "explanation": "{complication} triggered compensatory hemodynamic response",
    },
}


class CausalityBuilder:
    def __init__(self, ledger: List[Dict]):
        self.ledger = ledger
        self.graph = CausalityGraph()

    def build(self) -> CausalityGraph:
        self._load_nodes()
        self._link_causality()
        return self.graph

    def _load_nodes(self):
        for event in self.ledger:
            node = Node(
                id=event["id"],
                type=event["type"],
                tick=event.get("tick", -1),
                payload=event.get("payload", {}),
            )
            self.graph.add_node(node)

    COMP_WINDOW = 2

    def _link_causality(self):
        last_tick_event = None
        last_vitals_event = None
        active_complication = None
        complication_tick = None
        active_complication_name = None

        for node in list(self.graph.nodes.values()):
            if node.type == "tick":
                last_tick_event = node.id

            if complication_tick and (node.tick - complication_tick) > self.COMP_WINDOW:
                active_complication = None
                complication_tick = None
                active_complication_name = None

            if node.type == "complication":
                if last_vitals_event:
                    self.graph.add_edge(last_vitals_event, node.id, "physiology_trigger")
                active_complication = node.id
                complication_tick = node.tick
                active_complication_name = node.payload.get("complication", "unknown")

            if node.type == "procedure" and active_complication:
                self.graph.add_edge(active_complication, node.id, "clinical_response")

            if node.type == "vitals_update":
                has_recovery = (
                    active_complication is not None
                    and complication_tick is not None
                    and (node.tick - complication_tick) <= self.COMP_WINDOW
                )

                if has_recovery and last_tick_event is not None:
                    contract = COMPUTE_CONTRACTS["vitals_compute"]
                    explanation = contract.get("explanation", "").format(
                        complication=active_complication_name,
                    ) if active_complication_name else contract.get("explanation", "")
                    fid = self.graph.add_fusion_node(
                        tick=node.tick,
                        label="vitals_compute",
                        inputs=contract["inputs"],
                        policy=contract["policy"],
                        deterministic_key=contract["deterministic_key"],
                        explanation=explanation,
                    )
                    self.graph.add_edge(last_tick_event, fid, "tick_drives")
                    self.graph.add_edge(active_complication, fid, "recovery_effect")
                    self.graph.add_edge(fid, node.id, "computes")
                elif last_tick_event is not None:
                    self.graph.add_edge(last_tick_event, node.id, "tick_drives")

                last_vitals_event = node.id
