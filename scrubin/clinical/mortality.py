from scrubin.world.model import SimulationWorld

class MortalityModel:
    """
    Accumulates mortality risk continuously instead of binary failure.
    """
    
    @staticmethod
    def evaluate(world: SimulationWorld) -> float:
        risk_increase = 0.0
        
        # 1. Organ failure burden
        organs = [
            world.organ_state.cardiovascular.health,
            world.organ_state.respiratory.health,
            world.organ_state.renal.health
        ]
        
        for health in organs:
            if health < 0.5:
                risk_increase += 0.02 * (0.5 - health)
                
        # 2. Prolonged hypoxia
        spo2 = world.physiology.vitals.get("spo2", 100)
        if spo2 < 85:
            risk_increase += 0.05
            
        # 3. Unresolved shock (low MAP)
        sys = world.physiology.vitals.get("bp_systolic", 120)
        dia = world.physiology.vitals.get("bp_diastolic", 80)
        map_pressure = (sys + 2*dia) / 3.0
        if map_pressure < 60:
            risk_increase += 0.04
            
        # 4. SOFA Trend
        if world.sofa_score >= 8:
            risk_increase += 0.03
        if world.sofa_score >= 12:
            risk_increase += 0.06
            
        # Accumulate risk
        new_risk = min(1.0, world.mortality_risk + risk_increase)
        
        # Minor natural recovery if perfectly stable
        if risk_increase == 0.0 and world.sofa_score <= 2 and world.news2_score <= 2:
            new_risk = max(0.0, new_risk - 0.005)
            
        return new_risk
