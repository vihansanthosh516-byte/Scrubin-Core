import time
from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.experiments import ExperimentConfig
from scrubin.control_plane.streaming.channels import Topics
from scrubin.control_plane.observability.timeline import ExecutionTimeline
from scrubin.control_plane.observability.causal_trace import CausalTracer
from scrubin.control_plane.replay.state_diff_visualizer import StateDiffVisualizer
from scrubin.control_plane.ui.session_api import OperatorSessionAPI

def run_phase_12_5_demo():
    print("--- Phase 12.5: Real-time Streaming & Operator Observability Fabric ---")
    
    # 1. Initialize Kernel and Observability Tools
    kernel = ControlPlaneKernel(core_interface=None)
    timeline = ExecutionTimeline()
    causal_tracer = CausalTracer(kernel.event_stream)
    diff_visualizer = StateDiffVisualizer()
    operator_api = OperatorSessionAPI(kernel)
    
    # Subscribe timeline to stream
    kernel.event_stream.subscribe("*", timeline.ingest_event)
    
    # 2. Simulate Stream of Events (Vitals, Planning, Infrastructure)
    print("\n[Streaming] Ingesting live clinical and operational events...")
    session_id = "sess-alpha-1"
    
    # Tick 100: Normal Vitals
    kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "p1", "hr": 80, "spo2": 98}, tick=100, session_id=session_id)
    
    # Tick 101: Planner Decision
    kernel.event_stream.publish(Topics.MCTS_TRACE, {"chosen_action": "INTUBATE", "utility_delta": 0.5}, tick=101, session_id=session_id)
    
    # Tick 102: Deterioration (Triggering Alert)
    print("\n[Alerting] Simulating critical vitals drop...")
    kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "p1", "hr": 110, "spo2": 82}, tick=102, session_id=session_id)
    
    # Tick 103: Resource Alert
    kernel.event_stream.publish(Topics.NODE_HEALTH, {"node_id": "node-1", "load": 0.95}, tick=103, session_id=session_id)
    
    # 3. Operator API & Dashboard View
    print("\n[Operator API] Querying live session health...")
    health = operator_api.get_live_session_state(session_id)
    print(f"  - Latest Vitals: {health['vitals']}")
    print(f"  - Active Alerts Count: {len(health['active_alerts'])}")
    for alert in health['active_alerts']:
        print(f"    - [{alert['severity']}] {alert['message']}")
        
    # 4. State Diff Visualization
    print("\n[DiffVisualizer] Visualizing physiological shift (Tick 100 -> 102)...")
    old_state = {"vitals": {"hr": 80, "spo2": 98}}
    new_state = {"vitals": {"hr": 110, "spo2": 82}}
    print(diff_visualizer.generate_diff_view(old_state, new_state))
    
    # 5. Causal Reconstruction (Black Box Recorder)
    print("\n[CausalTracer] Reconstructing cause of deterioration for Patient p1...")
    explanation = causal_tracer.explain_outcome("p1", "hypoxia")
    print(f"  - Causal Chain Length: {len(explanation['causal_chain'])}")
    for factor in explanation['causal_chain']:
        print(f"    - Tick {factor['tick']}: {factor['rationale']} (Action: {factor['action']})")
        
    # 6. Timeline Reconstruction
    print("\n[Timeline] Reconstructing unified execution sequence...")
    ordered_timeline = timeline.get_ordered_timeline()
    print(f"  - Total Timeline Frames: {len(ordered_timeline)}")
    print(f"  - Sequence of Ticks: {[f.tick for f in ordered_timeline]}")

    print("\n--- Phase 12.5 Observability Fabric Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_5_demo()
