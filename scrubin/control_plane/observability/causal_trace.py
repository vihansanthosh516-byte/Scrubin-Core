from typing import List, Dict, Any, Optional
from scrubin.control_plane.streaming.event_stream import StreamEvent

class CausalTracer:
    """
    Clinical black box recorder: Performs causal reconstruction of simulation outcomes.
    """
    def __init__(self, event_stream: Any):
        self.stream = event_stream

    def explain_outcome(self, patient_id: str, outcome_type: str = "mortality") -> Dict[str, Any]:
        """
        Walks back from an outcome to find contributing causes.
        """
        # 1. Retrieve all events for this patient
        events = self.stream.replay(since_tick=0)
        p_events = [e for e in events if e.payload.get("patient_id") == patient_id]
        
        # 2. Identify critical deterioration points
        deterioration_ticks = []
        for e in p_events:
            if e.topic == "patient.vitals" and e.payload.get("spo2", 100) < 85:
                deterioration_ticks.append(e.tick)
                
        # 3. Match with planner decisions (including immediate history)
        causal_factors = []
        for tick in deterioration_ticks:
            # Look at current and preceding tick for causal decisions
            relevant_ticks = [tick, tick - 1]
            decision_events = [e for e in events if e.topic == "planner.mcts_trace" and e.tick in relevant_ticks]
            for de in decision_events:
                causal_factors.append({
                    "tick": de.tick,
                    "action": de.payload.get("chosen_action"),
                    "utility": de.payload.get("utility_delta"),
                    "rationale": f"Planner decision at tick {de.tick} correlated with deterioration at tick {tick}"
                })
                
        # 4. Check for resource constraints
        resource_alerts = [e for e in events if e.topic == "cluster.resource_alerts" and e.tick in deterioration_ticks]
        
        return {
            "patient_id": patient_id,
            "outcome": outcome_type,
            "causal_chain": causal_factors,
            "resource_contention": [e.payload for e in resource_alerts]
        }
