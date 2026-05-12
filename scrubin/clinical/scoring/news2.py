class NEWS2Score:
    """
    National Early Warning Score (NEWS) 2.
    Determines the degree of illness of a patient and prompts critical care intervention.
    """
    
    @staticmethod
    def calculate(vitals: dict) -> int:
        score = 0
        
        # Respiration rate (approximated via oxygenation distress if RR not available)
        spo2 = vitals.get("spo2", 100.0)
        if spo2 <= 91:
            score += 3
        elif spo2 <= 93:
            score += 2
        elif spo2 <= 95:
            score += 1
            
        # Systolic BP
        sys = vitals.get("bp_systolic", 120.0)
        if sys <= 90:
            score += 3
        elif sys <= 100:
            score += 2
        elif sys <= 110:
            score += 1
        elif sys >= 220:
            score += 3
            
        # Heart rate
        hr = vitals.get("heart_rate", 80.0)
        if hr <= 40:
            score += 3
        elif hr <= 50:
            score += 1
        elif hr >= 131:
            score += 3
        elif hr >= 111:
            score += 2
        elif hr >= 91:
            score += 1
            
        # Temperature
        temp = vitals.get("temperature", 36.5)
        if temp <= 35.0:
            score += 3
        elif temp <= 36.0:
            score += 1
        elif temp >= 39.1:
            score += 2
        elif temp >= 38.1:
            score += 1
            
        return score
