from scrubin.projections.base import Projection

class StateProjection(Projection):
    def __init__(self, patient_profile_id: str, mode: str):
        self.patient_profile_id = patient_profile_id
        self.mode = mode
        self.current_tick = 0
        self.latest_vitals = None
        self.active_complication = None
        self.latest_procedure = None
        
    def apply(self, event):
        self.current_tick = max(self.current_tick, event.tick)
        
        if event.type == "vitals_update":
            self.latest_vitals = event.payload.get("vitals", {})
            
        elif event.type == "complication":
            self.active_complication = {
                "complication": event.payload.get("complication"),
                "severity": event.payload.get("severity", "moderate"),
                "tick": event.tick,
                "sequence": event.id,
            }
            
        elif event.type == "procedure":
            self.latest_procedure = {
                "procedure": event.payload.get("procedure"),
                "target": event.payload.get("target"),
                "tick": event.tick,
                "sequence": event.id,
            }

    def get_snapshot(self):
        return {
            "tick": self.current_tick,
            "vitals": self.latest_vitals,
            "active_complication": self.active_complication,
            "last_procedure": self.latest_procedure,
            "patient_profile": self.patient_profile_id,
            "mode": self.mode,
        }
