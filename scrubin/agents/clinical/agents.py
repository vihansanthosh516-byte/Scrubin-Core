from typing import List
import uuid

from scrubin.decision.arbitration import ClinicalRecommendation
from scrubin.world.model import SimulationWorld

class ClinicalAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
    def evaluate(self, patient_id: str, world: SimulationWorld) -> List[ClinicalRecommendation]:
        """
        Agents operate on projections/copies (SimulationWorld) and produce recommendations.
        They do NOT mutate the world directly.
        """
        return []

class RespiratoryAgent(ClinicalAgent):
    def __init__(self):
        super().__init__("respiratory_agent_01")
        
    def evaluate(self, patient_id: str, world: SimulationWorld) -> List[ClinicalRecommendation]:
        recs = []
        vitals = world.physiology.vitals
        spo2 = vitals.get("spo2", 100)
        
        if spo2 < 85:
            recs.append(ClinicalRecommendation(
                id=f"rec-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                target_patient=patient_id,
                proposed_action="intubation",
                expected_utility=50.0,
                urgency=0.9,
                resource_cost=1.0,
                confidence=0.95,
                reasoning=["Severe hypoxia detected (SpO2 < 85)", "Immediate airway protection required"]
            ))
        elif spo2 < 92:
            recs.append(ClinicalRecommendation(
                id=f"rec-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                target_patient=patient_id,
                proposed_action="oxygen_therapy",
                expected_utility=20.0,
                urgency=0.6,
                resource_cost=0.1,
                confidence=0.85,
                reasoning=["Mild hypoxia detected", "Supplemental oxygen recommended"]
            ))
            
        return recs

class CardiologyAgent(ClinicalAgent):
    def __init__(self):
        super().__init__("cardiology_agent_01")
        
    def evaluate(self, patient_id: str, world: SimulationWorld) -> List[ClinicalRecommendation]:
        recs = []
        vitals = world.physiology.vitals
        sys = vitals.get("bp_systolic", 120)
        dia = vitals.get("bp_diastolic", 80)
        map_pressure = (sys + 2 * dia) / 3.0
        
        if map_pressure < 55:
            recs.append(ClinicalRecommendation(
                id=f"rec-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                target_patient=patient_id,
                proposed_action="vasopressors",
                expected_utility=45.0,
                urgency=0.95,
                resource_cost=0.5,
                confidence=0.9,
                reasoning=["Profound shock detected (MAP < 55)", "Vasopressor support required"]
            ))
        elif map_pressure < 65:
            recs.append(ClinicalRecommendation(
                id=f"rec-{uuid.uuid4().hex[:8]}",
                agent_id=self.agent_id,
                target_patient=patient_id,
                proposed_action="iv_fluids",
                expected_utility=15.0,
                urgency=0.5,
                resource_cost=0.2,
                confidence=0.8,
                reasoning=["Hypotension detected", "Fluid resuscitation recommended"]
            ))
            
        return recs
