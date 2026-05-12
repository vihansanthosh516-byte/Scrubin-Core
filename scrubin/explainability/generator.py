from dataclasses import dataclass
from typing import Optional

@dataclass
class EventExplanation:
    tick: int
    event_type: str
    target: str
    primary_reason: str
    contributing_factors: list[str]

class ExplanationGenerator:
    def __init__(self, ledger):
        self.ledger = ledger

    def explain_vital_change(self, tick: int, vital_name: str) -> EventExplanation:
        factors = []
        
        # Look backwards for procedures and complications
        for e in reversed(self.ledger.all()):
            if e.tick > tick:
                continue
            if e.tick < tick - 5:
                break
                
            if e.type == "procedure":
                factors.append(f"Recent {e.payload['procedure']} intervention")
            elif e.type == "complication_transition" and e.payload["to_status"] in ("escalating", "critical"):
                factors.append(f"Deterioration of {e.payload['complication']}")
                
        return EventExplanation(
            tick=tick,
            event_type="vital_change",
            target=vital_name,
            primary_reason="Physiological drift and active conditions",
            contributing_factors=factors
        )

    def explain_deterioration(self, patient_id: str) -> list[EventExplanation]:
        # Scans the ledger to build a narrative of why the patient deteriorated
        explanations = []
        for e in self.ledger.all():
            if e.type == "complication_transition" and e.payload["to_status"] == "escalating":
                factors = []
                # Check if interventions were missed
                recent_procs = [p for p in self.ledger.all() if p.type == "procedure" and p.tick >= e.tick - 5 and p.tick <= e.tick]
                if not recent_procs:
                    factors.append("Lack of timely intervention")
                
                explanations.append(EventExplanation(
                    tick=e.tick,
                    event_type="deterioration",
                    target=e.payload["complication"],
                    primary_reason="Natural disease progression",
                    contributing_factors=factors
                ))
        return explanations
