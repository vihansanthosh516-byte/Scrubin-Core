from dataclasses import dataclass

@dataclass
class OrganState:
    health: float = 1.0
    oxygen_demand: float = 1.0
    perfusion_status: float = 1.0

    def to_dict(self) -> dict:
        return {
            "health": round(self.health, 6),
            "oxygen_demand": round(self.oxygen_demand, 6),
            "perfusion_status": round(self.perfusion_status, 6),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OrganState":
        return cls(
            health=d.get("health", 1.0),
            oxygen_demand=d.get("oxygen_demand", 1.0),
            perfusion_status=d.get("perfusion_status", 1.0),
        )

class CardiovascularSystem:
    def __init__(self):
        self.state = OrganState()
        
    def evaluate(self, vitals: dict) -> OrganState:
        # MAP: Mean Arterial Pressure = (Systolic + 2*Diastolic)/3
        sys = vitals.get("bp_systolic", 120.0)
        dia = vitals.get("bp_diastolic", 80.0)
        map_pressure = (sys + 2*dia) / 3.0
        
        # Calculate perfusion based on MAP
        if map_pressure < 65:
            self.state.perfusion_status = max(0.1, map_pressure / 65.0)
            self.state.health -= 0.05 * (1.0 - self.state.perfusion_status)
        else:
            self.state.perfusion_status = 1.0
            self.state.health = min(1.0, self.state.health + 0.01)
            
        return self.state
