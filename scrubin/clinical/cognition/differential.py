import random
from dataclasses import dataclass, field
from typing import List, Dict, Any

from .diagnostics import ClinicalFinding
from scrubin.complications.registry import ComplicationRegistry


@dataclass
class DiagnosticHypothesis:
    condition: str
    probability: float
    evidence: List[ClinicalFinding] = field(default_factory=list)


class DifferentialEngine:
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        # Simplified symptom-to-condition mapping mapping for Bayesian inference
        # In a real system, this would be loaded from a configuration or medical database.
        self._symptom_map = {
            "tachycardia": {"hemorrhage": 0.8, "sepsis": 0.9, "arrhythmia": 0.7, "hypoxia": 0.6},
            "hypotension": {"hemorrhage": 0.9, "sepsis": 0.85, "anaphylaxis": 0.7},
            "hypoxia": {"pneumonia": 0.9, "pulmonary_embolism": 0.85, "atelectasis": 0.7, "hemorrhage": 0.4},
            "fever": {"sepsis": 0.9, "pneumonia": 0.8, "surgical_site_infection": 0.85},
        }

    def generate_differential(
        self,
        findings: List[ClinicalFinding],
        vitals: Dict[str, float],
        patient_profile: Any = None
    ) -> List[DiagnosticHypothesis]:
        """
        Generates a ranked list of differential diagnoses based on clinical findings.
        """
        hypotheses: Dict[str, float] = {}
        evidence_map: Dict[str, List[ClinicalFinding]] = {}
        
        # Base prior probabilities
        all_comps = ComplicationRegistry.get_ids()
        for comp in all_comps:
            hypotheses[comp] = 0.05  # Base prior
            evidence_map[comp] = []

        # Adjust based on findings
        for finding in findings:
            if finding.type in self._symptom_map:
                for condition, likelihood in self._symptom_map[finding.type].items():
                    if condition in hypotheses:
                        # Simple naive Bayes approximation for demonstration
                        # Posterior ~ Prior * Likelihood
                        # We sum the evidence for simplicity, but a full Bayesian update
                        # would multiply probabilities.
                        hypotheses[condition] += (likelihood * finding.confidence)
                        evidence_map[condition].append(finding)
                        
        # Normalize probabilities
        total_prob = sum(hypotheses.values())
        if total_prob > 0:
            for condition in hypotheses:
                hypotheses[condition] /= total_prob
                
        # Sort and return top hypotheses
        sorted_hypotheses = [
            DiagnosticHypothesis(condition=k, probability=v, evidence=evidence_map[k])
            for k, v in hypotheses.items() if v > 0.01
        ]
        sorted_hypotheses.sort(key=lambda x: x.probability, reverse=True)
        
        return sorted_hypotheses
