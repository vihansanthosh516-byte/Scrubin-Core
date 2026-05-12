from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import uuid

@dataclass
class ClinicalEvent:
    tick: int
    event_type: str
    description: str
    severity: str = "info"

@dataclass
class PatientHistory:
    patient_id: str
    prior_admissions: int = 0
    comorbidities: List[str] = field(default_factory=list)
    events: List[ClinicalEvent] = field(default_factory=list)
    
    def add_event(self, tick: int, event_type: str, description: str):
        self.events.append(ClinicalEvent(tick, event_type, description))

class ChronicDiseaseModel:
    """
    Simulates slow deterioration over weeks/months.
    """
    def __init__(self, disease_type: str):
        self.disease_type = disease_type
        self.deterioration_rate = 0.01 # Percentage per day
        self.flare_up_probability = 0.05 # Probability per week

    def step_day(self, patient_state: Dict[str, Any]):
        # Apply slow deterioration to relevant organ systems
        if self.disease_type == "COPD":
            patient_state["lung_capacity"] = patient_state.get("lung_capacity", 1.0) * (1 - self.deterioration_rate)
        elif self.disease_type == "CKD":
            patient_state["renal_function"] = patient_state.get("renal_function", 1.0) * (1 - self.deterioration_rate)

@dataclass
class PopulationGenerator:
    def generate_patient(self, cohort_type: str = "general_icu") -> PatientHistory:
        p_id = f"p-{uuid.uuid4().hex[:6]}"
        history = PatientHistory(patient_id=p_id)
        
        if cohort_type == "elderly_frail":
            history.comorbidities = ["HTN", "DM2", "CKD"]
            history.prior_admissions = 3
        elif cohort_type == "surgical_trauma":
            history.comorbidities = []
            history.prior_admissions = 0
            
        return history
