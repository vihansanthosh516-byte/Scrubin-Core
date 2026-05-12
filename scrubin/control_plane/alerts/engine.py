import time
import uuid
from typing import Dict, Any, List, Optional
from scrubin.control_plane.streaming.event_stream import EventStream
from scrubin.control_plane.streaming.channels import Topics

class AlertEngine:
    """
    Real-time clinical and operational alerting engine.
    """
    def __init__(self, event_stream: EventStream):
        self.stream = event_stream
        self.active_alerts: Dict[str, Dict[str, Any]] = {}

    def monitor_stream(self, event: Any):
        """
        Callback for the event stream to trigger rules-based alerts.
        """
        # Rule: SpO2 Critical Drop
        if event.topic == Topics.PATIENT_VITALS:
            if event.payload.get("spo2", 100) < 85:
                self.trigger_alert(
                    severity="CRITICAL",
                    message=f"Critical SpO2 drop detected for {event.payload.get('patient_id')}: {event.payload.get('spo2')}%",
                    tick=event.tick
                )
                
        # Rule: Cluster Overload
        if event.topic == Topics.NODE_HEALTH:
            if event.payload.get("load", 0) > 0.9:
                self.trigger_alert(
                    severity="WARNING",
                    message=f"Node {event.payload.get('node_id')} reporting near-saturation load.",
                    tick=event.tick
                )

    def trigger_alert(self, severity: str, message: str, tick: Optional[int] = None):
        alert_id = f"alert-{uuid.uuid4().hex[:6]}"
        alert = {
            "id": alert_id,
            "severity": severity,
            "message": message,
            "tick": tick or 0,
            "timestamp": time.time()
        }
        self.active_alerts[alert_id] = alert
        
        # Publish to event stream
        self.stream.publish(
            topic=Topics.CONTRACT_VIOLATIONS if severity in ("CRITICAL", "FATAL") else Topics.RESOURCE_ALERTS,
            payload=alert,
            tick=tick
        )
        print(f"[{severity}] ALERT: {message}")
