class ScoreEngine:
    def compute(self, ledger, findings):
        score = 100.0
        
        # Base penalties from structural findings
        for f in findings:
            if f.severity == "warn":
                score -= 5
            elif f.severity == "error":
                score -= 15
                
        # Trajectory-aware scoring
        complication_lifecycles = {}
        vitals_history = []
        interventions = 0
        
        for event in ledger:
            if event.type == "complication_transition":
                comp_id = event.payload["complication"]
                to_status = event.payload["to_status"]
                complication_lifecycles.setdefault(comp_id, []).append(to_status)
                if to_status == "escalating":
                    score -= 5  # escalating-state penalty
                elif to_status == "unstable":
                    score -= 10 # instability duration penalty
                    
            elif event.type == "vitals_update":
                vitals_history.append(event.payload["vitals"])
                
            elif event.type == "decision_execution" and event.payload.get("executed"):
                interventions += 1
                
        # Physiologic volatility scoring (smoothness)
        if len(vitals_history) > 1:
            for i in range(1, len(vitals_history)):
                v_prev = vitals_history[i-1]
                v_curr = vitals_history[i]
                if "spo2" in v_curr and "spo2" in v_prev:
                    delta = abs(v_curr["spo2"] - v_prev["spo2"])
                    if delta > 10.0:
                        score -= 2 # penalty for volatile jumps
                        
        # Excessive intervention penalties
        if interventions > 5:
            score -= (interventions - 5) * 5
            
        # Unresolved complication penalties
        for comp_id, transitions in complication_lifecycles.items():
            if not transitions or transitions[-1] not in ("resolved", "latent"):
                score -= 10

        return max(0, int(score))
