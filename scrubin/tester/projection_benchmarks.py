import time
import random
from scrubin.core.ledger import EventLedger
from scrubin.projections.state import StateProjection
from scrubin.projections.event import EventProjection

def simulate_old_snapshot(ledger, patient_id, mode):
    # Old way: scan entire ledger
    current_tick = 0
    vitals = None
    complication = None
    procedure = None
    for event in ledger.all():
        current_tick = max(current_tick, event.tick)
        if event.type == "vitals_update":
            vitals = event.payload.get("vitals", {})
        elif event.type == "complication":
            complication = {
                "complication": event.payload.get("complication"),
                "severity": event.payload.get("severity", "moderate"),
                "tick": event.tick,
            }
        elif event.type == "procedure":
            procedure = {
                "procedure": event.payload.get("procedure"),
                "target": event.payload.get("target"),
                "tick": event.tick,
            }
    return {
        "tick": current_tick,
        "vitals": vitals,
        "active_complication": complication,
        "last_procedure": procedure,
        "patient_profile": patient_id,
        "mode": mode,
    }

def run_benchmarks():
    print("--- Projections Benchmark ---")
    
    # 1. Setup simulated ledger with 100,000 events
    ledger = EventLedger()
    state_proj = StateProjection("test_patient", "autonomous")
    event_proj = EventProjection(max_history=100000)
    
    ledger.add_listener(state_proj.apply)
    ledger.add_listener(event_proj.apply)
    
    print("Generating 10,000 events...")
    
    start_gen = time.time()
    for i in range(10000):
        tick = i // 10
        event_type = random.choice(["vitals_update", "complication", "procedure", "other"])
        ledger.log(event_type, {"value": i}, tick=tick)
    gen_time = time.time() - start_gen
    
    print(f"Generated and projected 10,000 events in {gen_time:.4f}s")
    print(f"Projection Update Latency: {(gen_time/10000)*1000:.4f} ms per event\n")
    
    # 2. Snapshot Retrieval Time
    start_old = time.time()
    for _ in range(100):
        _ = simulate_old_snapshot(ledger, "test_patient", "autonomous")
    old_snap_time = time.time() - start_old
    
    start_new = time.time()
    for _ in range(100):
        _ = state_proj.get_snapshot()
    new_snap_time = time.time() - start_new
    
    print("Snapshot Retrieval Time (100 calls):")
    print(f"  Old (Ledger Scan): {old_snap_time:.4f}s")
    print(f"  New (O(1) Projection): {new_snap_time:.4f}s")
    if old_snap_time > 0 and new_snap_time > 0:
        print(f"  Speedup: {old_snap_time / new_snap_time:.1f}x\n")
    
    # 3. Event Streaming Throughput
    start_old_events = time.time()
    for _ in range(100):
        res = []
        for e in ledger.all():
            if e.id > 9000:
                res.append(e)
    old_events_time = time.time() - start_old_events
    
    start_new_events = time.time()
    for _ in range(100):
        _ = event_proj.events_after(9000)
    new_events_time = time.time() - start_new_events
    
    print("Incremental Event Replay (sequence > 9000) (100 calls):")
    print(f"  Old (Ledger Scan): {old_events_time:.4f}s")
    print(f"  New (Event Projection): {new_events_time:.4f}s")
    if old_events_time > 0 and new_events_time > 0:
        print(f"  Speedup: {old_events_time / new_events_time:.1f}x\n")

if __name__ == "__main__":
    run_benchmarks()
