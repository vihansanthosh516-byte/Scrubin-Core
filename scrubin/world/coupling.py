from scrubin.world.model import SimulationWorld

class SystemCouplingGraph:
    """
    Centralizes all cross-system influences.
    e.g., organ failure -> vitals deterioration, resource shortage -> mortality.
    """
    
    @staticmethod
    def evaluate_vital_influences(world: SimulationWorld) -> dict[str, float]:
        vitals_modifiers = {}
        
        # Cardiovascular collapse drops perfusion everywhere (simulated via BP drop)
        cv_health = world.organ_state.cardiovascular.health
        if cv_health < 0.8:
            vitals_modifiers["bp_systolic"] = -10.0 * (1.0 - cv_health)
            vitals_modifiers["bp_diastolic"] = -5.0 * (1.0 - cv_health)
            
        # Respiratory failure -> Hypoxia and Cardiac stress
        resp_health = world.organ_state.respiratory.health
        if resp_health < 0.8:
            vitals_modifiers["spo2"] = -5.0 * (1.0 - resp_health)
            vitals_modifiers["heart_rate"] = 15.0 * (1.0 - resp_health)
            
        # Renal failure -> Metabolic instability
        renal_health = world.organ_state.renal.health
        if renal_health < 0.8:
            vitals_modifiers["heart_rate"] = vitals_modifiers.get("heart_rate", 0) + 10.0 * (1.0 - renal_health)
            vitals_modifiers["bp_systolic"] = vitals_modifiers.get("bp_systolic", 0) - 5.0 * (1.0 - renal_health)
            
        return vitals_modifiers

    @staticmethod
    def apply_organ_cascades(world: SimulationWorld):
        # Cascades where one organ failing hurts another
        
        # Severe hypoxia hurts the cardiovascular system
        if world.organ_state.respiratory.health < 0.5:
            world.organ_state.cardiovascular.health -= 0.02
            
        # Severe cardiovascular collapse hurts renal system (already handled natively in renal evaluation)
        # but we can enforce it here if we want pure decoupling.

    @staticmethod
    def apply_resource_cascades(world: SimulationWorld):
        # Example: No ICU beds available increases instability
        pass
