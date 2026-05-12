from typing import Dict, List, Any, Optional
from scrubin.control_plane.streaming.event_stream import EventStream

class OperatorSessionAPI:
    """
    Operator-facing API layer for retrieving live session state and traces.
    """
    def __init__(self, kernel: Any):
        self.kernel = kernel
        self.stream: EventStream = kernel.event_stream

    def get_live_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Aggregates latest vitals, alerts, and node health for a session.
        """
        # 1. Get latest vitals from stream
        vitals_events = self.stream.replay(topic="patient.vitals")
        latest_vitals = vitals_events[-1].payload if vitals_events else {}
        
        # 2. Get active alerts
        alerts = self.stream.replay(topic="verification.contract_violation")
        
        # 3. Get cluster health
        cluster_stats = self.kernel.dist_adapter.telemetry.get_cluster_stats()
        
        return {
            "session_id": session_id,
            "vitals": latest_vitals,
            "active_alerts": [a.payload for a in alerts[-5:]],
            "cluster_health": cluster_stats
        }

    def query_trajectory(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Returns the historical vital trajectory for a specific patient.
        """
        vitals = self.stream.replay(topic="patient.vitals")
        return [v.payload for v in vitals if v.payload.get("patient_id") == patient_id]
