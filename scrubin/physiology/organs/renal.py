from .cardiovascular import OrganState

class RenalSystem:
    def __init__(self):
        self.state = OrganState()
        self.urine_output_ml_per_kg_hr = 1.0
        
    def evaluate(self, cardiovascular_state: OrganState) -> OrganState:
        # Kidneys are highly sensitive to perfusion
        if cardiovascular_state.perfusion_status < 0.8:
            self.state.health -= 0.08 * (1.0 - cardiovascular_state.perfusion_status)
            self.urine_output_ml_per_kg_hr = max(0.0, 1.0 * cardiovascular_state.perfusion_status)
        else:
            self.state.health = min(1.0, self.state.health + 0.005)
            self.urine_output_ml_per_kg_hr = 1.0
            
        return self.state
