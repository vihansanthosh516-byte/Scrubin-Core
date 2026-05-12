from .cardiovascular import OrganState

class RespiratorySystem:
    def __init__(self):
        self.state = OrganState()
        
    def evaluate(self, vitals: dict) -> OrganState:
        spo2 = vitals.get("spo2", 100.0)
        
        if spo2 < 90.0:
            severity = (90.0 - spo2) / 90.0
            self.state.oxygen_demand = 1.0 + severity
            self.state.health -= 0.05 * severity
        else:
            self.state.oxygen_demand = 1.0
            self.state.health = min(1.0, self.state.health + 0.01)
            
        return self.state
