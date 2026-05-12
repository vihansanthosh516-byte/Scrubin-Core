from scrubin.projections.base import Projection

class DecisionProjection(Projection):
    def __init__(self):
        self.latest_options = []
        self.latest_decision = None
        self.latest_validation = None
        self.latest_execution = None
        self.current_tick = 0
        
    def apply(self, event):
        self.current_tick = max(self.current_tick, event.tick)
        
        if event.type == "decision_options":
            self.latest_options = event.payload.get("options", [])
            
        elif event.type == "decision":
            d = dict(event.payload)
            d["sequence"] = event.id
            d["tick"] = event.tick
            self.latest_decision = d
            
        elif event.type == "decision_validation":
            d = dict(event.payload)
            d["sequence"] = event.id
            self.latest_validation = d
            if self.latest_decision and self.latest_decision["tick"] == event.tick:
                self.latest_decision["validation"] = event.payload
                
        elif event.type == "decision_execution":
            d = dict(event.payload)
            d["sequence"] = event.id
            self.latest_execution = d
            if self.latest_decision and self.latest_decision["tick"] == event.tick:
                self.latest_decision["execution"] = event.payload

    def get_snapshot(self):
        return {
            "options": self.latest_options,
            "last_decision": self.latest_decision,
            "last_validation": self.latest_validation,
            "last_execution": self.latest_execution,
        }
