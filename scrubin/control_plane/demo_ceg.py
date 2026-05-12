from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.streaming.channels import Topics
from scrubin.control_plane.causal_graph.engine import EdgeType

def run_causal_graph_demo():
    print("--- Phase 12.6b: Causal Execution Graph (CEG) ---")
    
    # 1. Initialize Kernel (Causal Graph is built-in)
    kernel = ControlPlaneKernel(core_interface=None)
    
    # 2. Simulate a Causal Chain
    # [Infrastructure Latency] -> [Planner Decision] -> [Clinical Change]
    print("\n[Simulation] Ingesting causally linked event sequence...")
    
    # Tick 10: Infrastructure Latency
    kernel.event_stream.publish(
        Topics.NODE_HEALTH, 
        {"category": "INFRASTRUCTURE", "node_id": "worker-1", "latency": 500}, 
        tick=10
    )
    
    # Tick 11: Clinical Deterioration
    kernel.event_stream.publish(
        Topics.PATIENT_VITALS, 
        {"category": "CLINICAL", "patient_id": "p1", "spo2": 85}, 
        tick=11
    )
    
    # Tick 12: Planner Action (Responds to deterioration)
    kernel.event_stream.publish(
        Topics.MCTS_TRACE, 
        {"category": "PLANNER", "chosen_action": "INCREASE_O2", "utility_delta": 0.8}, 
        tick=12
    )
    
    # Tick 15: Clinical Recovery (Caused by action)
    kernel.event_stream.publish(
        Topics.PATIENT_VITALS, 
        {"category": "CLINICAL", "patient_id": "p1", "spo2": 95}, 
        tick=15
    )
    
    # 3. Query the Graph
    print("\n[Causal Graph] Analyzing execution dependencies...")
    
    # Find the recovery event
    recovery_event = [ev for ev in kernel.semantic_history if ev.topic == Topics.PATIENT_VITALS and ev.payload.get("spo2") == 95][0]
    
    print(f"\n[Root Cause Analysis] Finding upstream causes of Recovery ({recovery_event.event_id}):")
    causes = kernel.causal_graph.get_upstream_causes(recovery_event.event_id)
    for cause in causes:
        print(f"  <- {cause.category}: {cause.topic} at tick {cause.timestamp_tick} (Payload: {cause.payload})")
        
    # Find the planner action event
    action_event = [ev for ev in kernel.semantic_history if ev.category == "PLANNER"][0]
    
    print(f"\n[Impact Analysis] Finding downstream effects of Planner Action ({action_event.event_id}):")
    effects = kernel.causal_graph.get_downstream_effects(action_event.event_id)
    for effect in effects:
        print(f"  -> {effect.category}: {effect.topic} at tick {effect.timestamp_tick} (Payload: {effect.payload})")

    print("\n--- Causal Execution Graph Demo Complete ---")

if __name__ == "__main__":
    run_causal_graph_demo()
