from scrubin.control_plane.kernel import ControlPlaneKernel
from scrubin.control_plane.streaming.channels import Topics
from scrubin.control_plane.schema_registry.registry import EventSchema
from scrubin.control_plane.tracing.correlator import TraceContext
from scrubin.control_plane.query.query_engine import SemanticQueryEngine
from scrubin.control_plane.compression.event_compactor import EventCompactor
from scrubin.control_plane.forensics.divergence_detector import DivergenceForensics

def run_phase_12_6_demo():
    print("--- Phase 12.6: Semantic Execution Intelligence & Forensics ---")
    
    # 1. Initialize Kernel and Semantic Tools
    kernel = ControlPlaneKernel(core_interface=None)
    compactor = EventCompactor()
    forensics = DivergenceForensics()
    
    # 2. Schema Validation Test
    print("\n[Schema] Validating event against versioned registry...")
    good_payload = {"patient_id": "p1", "hr": 80, "spo2": 98}
    bad_payload = {"patient_id": "p1", "hr": "UNKNOWN"} # Type mismatch
    
    is_good = kernel.schema_registry.validate(Topics.PATIENT_VITALS, 1, good_payload)
    is_bad = kernel.schema_registry.validate(Topics.PATIENT_VITALS, 1, bad_payload)
    
    print(f"  - Valid Payload (p1, 80, 98): {is_good}")
    print(f"  - Invalid Payload (hr: 'UNKNOWN'): {is_bad}")
    
    # 3. Distributed Trace Reconstruction
    print("\n[Tracing] Simulating causally linked distributed events...")
    # Mortality -> Planner Decision -> Resource Alert
    root_trace = TraceContext(session_id="sess-1", patient_id="p1")
    child_trace = TraceContext(parent_id=root_trace.trace_id, session_id="sess-1")
    
    kernel.event_stream.publish(Topics.MORTALITY_EVENTS, {"patient_id": "p1"}, tick=200)
    # (In real kernel, we would link these via trace_id)
    
    # 4. Divergence Forensics (Replay Mismatch)
    print("\n[Forensics] Detecting simulation divergence between distributed nodes...")
    node_a_vitals = {"hr": 80, "spo2": 95}
    node_b_vitals = {"hr": 80, "spo2": 92} # 3% drift
    
    divergence = forensics.detect_mismatch(node_a_vitals, node_b_vitals)
    if divergence:
        print(f"  - Divergence Found: {divergence['type']}")
        print(f"  - Diffs: {divergence['diff']}")
        
    # 5. Semantic Replay Compression
    print("\n[Compression] Compressing high-frequency telemetry...")
    raw_events = [
        {"topic": "vitals", "payload": {"hr": 80, "spo2": 98}},
        {"topic": "vitals", "payload": {"hr": 80, "spo2": 98}}, # Duplicate (Delta should catch)
        {"topic": "vitals", "payload": {"hr": 81, "spo2": 98}}, # Change
        {"topic": "mortality", "payload": {"critical": True}} # Critical (Keep)
    ]
    compacted = compactor.compact_batch(raw_events)
    print(f"  - Raw Event Count: {len(raw_events)}")
    print(f"  - Compacted Count: {len(compacted)}")
    print(f"  - Compression Ratio: {len(raw_events)/len(compacted):.1f}x")
    
    # 6. Semantic Query Engine
    print("\n[Query] Executing semantic search over execution history...")
    query_engine = SemanticQueryEngine(kernel.semantic_history)
    
    # Manually ingest some events to semantic history for demo
    kernel.event_stream.publish(Topics.PATIENT_VITALS, {"patient_id": "p1", "hr": 70, "spo2": 90}, tick=10)
    kernel.event_stream.publish(Topics.MORTALITY_EVENTS, {"patient_id": "p1"}, tick=100)
    
    # Find all mortality events
    mortality_evs = query_engine.query(lambda e: e.topic == Topics.MORTALITY_EVENTS)
    print(f"  - Found {len(mortality_evs)} mortality events in history.")
    
    # Aggregate by category
    stats = query_engine.aggregate_by_category()
    print(f"  - Event Categories: {stats}")

    print("\n--- Phase 12.6 Semantic Intelligence Demo Complete ---")

if __name__ == "__main__":
    run_phase_12_6_demo()
