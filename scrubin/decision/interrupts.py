from scrubin.world.model import SimulationWorld
from typing import Optional

class EmergencyInterrupts:
    """
    Bypasses deep strategic planning when immediate life-saving interventions are required.
    """
    @staticmethod
    def check_interrupt(world: SimulationWorld) -> Optional[str]:
        vitals = world.physiology.vitals
        
        # 1. Cardiac Arrest / Extreme Shock
        sys = vitals.get("bp_systolic", 120)
        dia = vitals.get("bp_diastolic", 80)
        map_pressure = (sys + 2*dia) / 3.0
        if map_pressure < 50:
            return "vasopressors"
            
        # 2. Critical Hypoxia
        spo2 = vitals.get("spo2", 100)
        if spo2 < 70:
            return "intubation"
            
        # 3. Severe Bradycardia
        hr = vitals.get("heart_rate", 80)
        if hr < 40:
            return "emergency_intervention"
            
        return None
