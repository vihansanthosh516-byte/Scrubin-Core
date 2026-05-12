from scrubin.tester.models import TestFinding


class StructureCheck:
    REQUIRED_EVENT_TYPES = {"system.boot", "tick", "vitals_update"}

    def run(self, ledger):
        findings = []
        seen_types = set()

        for event in ledger:
            seen_types.add(event.type)

        missing = self.REQUIRED_EVENT_TYPES - seen_types
        for event_type in missing:
            findings.append(TestFinding(
                severity="error",
                message=f"Missing required event type: {event_type}",
            ))

        if not any(e.type == "system.boot" for e in ledger):
            findings.append(TestFinding(
                severity="error",
                message="No system.boot event found",
            ))

        tick_events = [e for e in ledger if e.type == "tick"]
        ticks_seen = {e.payload.get("tick") for e in tick_events}
        if len(ticks_seen) != len(tick_events):
            findings.append(TestFinding(
                severity="warn",
                message="Duplicate tick numbers detected",
            ))

        return findings
