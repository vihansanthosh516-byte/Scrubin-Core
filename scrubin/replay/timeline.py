from dataclasses import dataclass

@dataclass
class TimelineEvent:
    tick: int
    category: str
    title: str
    details: dict

class TimelineGenerator:
    def __init__(self, ledger):
        self.ledger = ledger

    def generate(self) -> list[TimelineEvent]:
        timeline = []
        for e in self.ledger.all():
            if e.type == "complication":
                timeline.append(TimelineEvent(
                    tick=e.tick,
                    category="complication",
                    title=f"Onset: {e.payload['complication']}",
                    details={"severity": e.payload["severity"]}
                ))
            elif e.type == "complication_transition":
                timeline.append(TimelineEvent(
                    tick=e.tick,
                    category="clinical_state",
                    title=f"State Change: {e.payload['complication']}",
                    details={"from": e.payload["from_status"], "to": e.payload["to_status"]}
                ))
            elif e.type == "procedure":
                timeline.append(TimelineEvent(
                    tick=e.tick,
                    category="intervention",
                    title=f"Procedure: {e.payload['procedure']}",
                    details={"target": e.payload["target"]}
                ))
            elif e.type == "vitals_update":
                # Only log critical vital events
                spo2 = e.payload.get("vitals", {}).get("spo2", 100)
                if spo2 < 90:
                    timeline.append(TimelineEvent(
                        tick=e.tick,
                        category="critical_vital",
                        title="Critical Hypoxia Detected",
                        details={"spo2": spo2}
                    ))
        
        return sorted(timeline, key=lambda x: x.tick)
