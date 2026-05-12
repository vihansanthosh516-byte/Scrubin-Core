class SOFAScore:
    """
    Sequential Organ Failure Assessment (SOFA) score.
    Used to track a patient's status during their stay in an ICU.
    """
    
    @staticmethod
    def calculate(vitals: dict, organ_states: dict = None) -> int:
        score = 0
        
        # Respiratory (PaO2/FiO2 ratio approximated via SpO2)
        spo2 = vitals.get("spo2", 100)
        if spo2 < 90:
            score += 2
        elif spo2 < 94:
            score += 1
            
        # Cardiovascular (MAP and vasopressors)
        sys = vitals.get("bp_systolic", 120)
        dia = vitals.get("bp_diastolic", 80)
        map_pressure = (sys + 2*dia) / 3.0
        
        if map_pressure < 70:
            score += 1
        if map_pressure < 65: # Approximating vasopressor requirement
            score += 3
            
        # Renal (creatinine / urine output)
        if organ_states and "renal" in organ_states:
            renal_health = organ_states["renal"].health
            if renal_health < 0.5:
                score += 3
            elif renal_health < 0.8:
                score += 1
                
        return score
