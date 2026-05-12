import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class HiddenCondition:
    id: str
    severity: str
    onset_tick: int
    observability: float
    progression_rate: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "onset_tick": self.onset_tick,
            "observability": round(self.observability, 6),
            "progression_rate": round(self.progression_rate, 6),
        }


@dataclass
class ClinicalFinding:
    type: str
    confidence: float
    source: str
    supporting_vitals: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "confidence": round(self.confidence, 6),
            "source": self.source,
            "supporting_vitals": dict(sorted(self.supporting_vitals.items())),
            "timestamp": self.timestamp,
        }


@dataclass
class DiagnosticHypothesis:
    condition: str
    probability: float
    evidence: List[ClinicalFinding] = field(default_factory=list)
    confidence_interval: tuple[float, float] = (0.0, 1.0)

    def to_dict(self) -> dict:
        return {
            "condition": self.condition,
            "probability": round(self.probability, 6),
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence_interval": [round(c, 6) for c in self.confidence_interval],
        }


class BayesianUpdater:
    @staticmethod
    def update_posterior(prior: float, likelihood: float, false_positive_rate: float = 0.1) -> float:
        if prior >= 1.0: return 1.0
        if prior <= 0.0: return 0.0
        evidence_prob = (likelihood * prior) + (false_positive_rate * (1 - prior))
        if evidence_prob == 0: return 0.0
        return (likelihood * prior) / evidence_prob


class DifferentialEngine:
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
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
        priors: Optional[Dict[str, float]] = None
    ) -> List[DiagnosticHypothesis]:
        hypotheses: Dict[str, float] = priors or {}
        evidence_map: Dict[str, List[ClinicalFinding]] = {k: [] for k in hypotheses}
        
        # If no priors provided, initialize with small base prior
        if not hypotheses:
            conditions = set()
            for targets in self._symptom_map.values():
                conditions.update(targets.keys())
            for cond in conditions:
                hypotheses[cond] = 0.05
                evidence_map[cond] = []

        # Update based on findings
        for finding in findings:
            if finding.type in self._symptom_map:
                for condition, likelihood in self._symptom_map[finding.type].items():
                    if condition in hypotheses:
                        hypotheses[condition] = BayesianUpdater.update_posterior(
                            hypotheses[condition], 
                            likelihood * finding.confidence
                        )
                        evidence_map[condition].append(finding)
                        
        # Normalize
        total_prob = sum(hypotheses.values())
        if total_prob > 0:
            for condition in hypotheses:
                hypotheses[condition] /= total_prob
                
        # Sort and return
        results = [
            DiagnosticHypothesis(
                condition=k, 
                probability=v, 
                evidence=evidence_map[k],
                confidence_interval=(max(0, v - 0.1), min(1, v + 0.1)) # Simulated CI
            )
            for k, v in hypotheses.items() if v > 0.01
        ]
        results.sort(key=lambda x: x.probability, reverse=True)
        return results
