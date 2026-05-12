from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TreatmentPathway:
    id: str
    description: str
    steps: List[str]
    indications: List[str]
    contraindications: List[str]


@dataclass
class MedicalOntology:
    id: str
    label: str
    category: str  # 'procedure', 'medication', 'organ', 'finding'
    properties: Dict[str, Any] = field(default_factory=dict)
    related_to: List[str] = field(default_factory=list)


class ClinicalKnowledgeLayer:
    """
    Structured medical ontology and treatment knowledge.
    Provides a symbolic backbone for planners and explainability engines.
    """
    def __init__(self):
        self.ontology: Dict[str, MedicalOntology] = {}
        self.pathways: Dict[str, TreatmentPathway] = {}
        self._load_canonical_knowledge()

    def _load_canonical_knowledge(self):
        # Procedures
        self.add_ontology(MedicalOntology(
            id="intubation", label="Endotracheal Intubation", category="procedure",
            properties={"invasive": True, "risk": "high"},
            related_to=["hypoxia", "respiratory_failure"]
        ))
        
        self.add_ontology(MedicalOntology(
            id="fluid_bolus", label="Fluid Resuscitation", category="procedure",
            properties={"invasive": False, "risk": "low"},
            related_to=["hypotension", "hemorrhage"]
        ))

        # Pathways
        self.pathways["septic_shock"] = TreatmentPathway(
            id="septic_shock_pathway",
            description="Escalation ladder for septic shock",
            steps=["fluid_bolus", "vasopressors", "intubation"],
            indications=["fever", "hypotension", "tachycardia"],
            contraindications=["fluid_overload"]
        )

    def add_ontology(self, item: MedicalOntology):
        self.ontology[item.id] = item

    def get_related(self, entity_id: str) -> List[MedicalOntology]:
        if entity_id not in self.ontology:
            return []
        return [self.ontology[rid] for rid in self.ontology[entity_id].related_to if rid in self.ontology]

    def query_by_category(self, category: str) -> List[MedicalOntology]:
        return [v for v in self.ontology.values() if v.category == category]
