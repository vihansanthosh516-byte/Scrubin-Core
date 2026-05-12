from typing import Dict, Any, List, Optional
from scrubin.control_plane.ir.model import IRNode, IREdge, IRGraph
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.jobs import Job, JobType

class IRCompiler:
    """
    Transforms Intent (Experiments/Jobs) into a formal SIR Graph.
    """
    def compile(self, experiment: ExperimentConfig, world_context: Dict[str, Any]) -> IRGraph:
        graph = IRGraph(metadata={"experiment_id": experiment.id})
        
        # Step 1: Initialize System Infrastructure Nodes
        snapshot_node = IRNode(type="SNAPSHOT", payload={"mode": "FORK"}, tick_offset=0)
        audit_node = IRNode(type="AUDIT_LOG", payload={"level": "CORE"}, tick_offset=0)
        graph.nodes.extend([snapshot_node, audit_node])
        
        # Step 2: Expand Job Nodes based on Experiment Type
        if experiment.vectorized:
            self._compile_vectorized_workload(graph, experiment)
        else:
            self._compile_standard_workload(graph, experiment)
            
        # Step 3: Inject Control & Verification Nodes
        contract_check = IRNode(type="CONTRACT_CHECK", payload={"schema": "ExperimentSchema"})
        graph.nodes.append(contract_check)
        
        # Step 4: Link Nodes (Simplified dependency chain)
        for i in range(len(graph.nodes) - 1):
            graph.edges.append(IREdge(src=graph.nodes[i].id, dst=graph.nodes[i+1].id))
            
        return graph

    def _compile_standard_workload(self, graph: IRGraph, experiment: ExperimentConfig):
        # Clinical eval cycle
        vitals_node = IRNode(type="VITALS_EVAL", tick_offset=0)
        organs_node = IRNode(type="ORGANS_EVAL", tick_offset=0)
        decision_node = IRNode(type="MCTS_DECISION", payload={"iterations": 1000}, tick_offset=1)
        
        graph.nodes.extend([vitals_node, organs_node, decision_node])
        
        if experiment.governance_enabled:
            gov_node = IRNode(type="RESOURCE_CHECK", payload={"target": "HOSPITAL_LOAD"})
            graph.nodes.append(gov_node)

    def _compile_vectorized_workload(self, graph: IRGraph, experiment: ExperimentConfig):
        # Parallel batch evaluation
        vector_node = IRNode(type="VECTOR_BATCH", payload={"size": experiment.cohort_size})
        graph.nodes.append(vector_node)
