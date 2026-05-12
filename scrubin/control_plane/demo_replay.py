from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.streaming.channels import Topics
from scrubin.control_plane.replay.state import ReplayState

def run_replay_demo():
    print("--- Phase 12.7: Deterministic Replay Engine ---")
    
    # 1. Initialize Kernel
    kernel = ControlPlaneKernel(core_interface=None)
    session_id = "replay-sess-1"
    
    # 2. Ingest Events in "Shuffled" Order
    # Causal Order: 1. Vitals(80) -> 2. Action(O2) -> 3. Vitals(95)
    # We ingest: 2 then 1 then 3
    print("\n[Ingestion] Ingesting events in out-of-order sequence...")
    
    # Tick 12: Planner Action
    kernel.event_stream.publish(
        Topics.MCTS_TRACE, 
        {"category": "PLANNER", "chosen_action": "INCREASE_O2"}, 
        tick=12, session_id=session_id
    )
    
    # Tick 11: Clinical Deterioration
    kernel.event_stream.publish(
        Topics.PATIENT_VITALS, 
        {"category": "CLINICAL", "patient_id": "p1", "spo2": 80}, 
        tick=11, session_id=session_id
    )
    
    # Tick 15: Clinical Recovery
    kernel.event_stream.publish(
        Topics.PATIENT_VITALS, 
        {"category": "CLINICAL", "patient_id": "p1", "spo2": 95}, 
        tick=15, session_id=session_id
    )
    
    # 3. Perform Replay
    print("\n[Replay] Reconstructing session state via topological causal sort...")
    result = kernel.replay.reconstruct_session(session_id)
    
    # 4. Verify Execution Order
    print(f"\n[Validation] Replayed {len(result['execution_order'])} events.")
    print(f"  - Execution Order (Event IDs): {result['execution_order']}")
    
    # Verify topological order (Vitals 80 MUST come before Action O2)
    ordered_topics = [kernel.causal_graph.nodes[eid].topic for eid in result['execution_order']]
    print(f"  - Topic Order: {ordered_topics}")
    
    # 5. Verify Final State
    final_state = result["final_state"]
    print(f"\n[Final State] Session reconstruction complete:")
    print(f"  - Final SpO2: {final_state.vitals.get('spo2')}%")
    print(f"  - Final Tick: {final_state.tick}")
    print(f"  - Decisions Made: {len(final_state.decisions)}")
    
    # 6. Verify Snapshot Integrity (Jump Debugging)
    print("\n[Snapshots] Verifying snapshot consistency...")
    first_event_id = result['execution_order'][0]
    snapshot_at_first = result['snapshots'][first_event_id]
    print(f"  - SpO2 at first event ({first_event_id}): {snapshot_at_first.vitals.get('spo2')}%")
    
    # 7. Determinism Test: Double Replay Equality
    print("\n[Determinism] Testing double replay equality...")
    result2 = kernel.replay.reconstruct_session(session_id)
    assert result["final_state"] == result2["final_state"]
    print("  - SUCCESS: Replay is strictly deterministic.")

    print("\n--- Deterministic Replay Engine Demo Complete ---")

if __name__ == "__main__":
    run_replay_demo()
