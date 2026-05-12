from scrubin.tester.models import TestFinding
from scrubin.core.config import ConfigLayer


class CausalityCheck:
    def __init__(self, config: ConfigLayer = None):
        self._config = config or ConfigLayer()

    def run(self, ledger):
        findings = []
        response_window = self._config.get("procedures.yaml", "recovery_window", 5)

        complications = [e for e in ledger if e.type == "complication"]
        procedures = [e for e in ledger if e.type == "procedure"]

        for comp in complications:
            comp_tick = comp.tick
            has_procedure = any(
                p.tick >= comp_tick and p.tick <= comp_tick + response_window
                for p in procedures
            )
            if not has_procedure:
                findings.append(TestFinding(
                    severity="warn",
                    message=f"Complication '{comp.payload.get('complication')}' at tick {comp_tick} has no clinical response within {response_window} ticks",
                    tick=comp_tick,
                ))

        for proc in procedures:
            target = proc.payload.get("target")
            has_complication = any(
                c.payload.get("complication") == target and c.tick <= proc.tick
                for c in complications
            )
            if not has_complication:
                findings.append(TestFinding(
                    severity="error",
                    message=f"Procedure '{proc.payload.get('procedure')}' at tick {proc.tick} has no matching complication",
                    tick=proc.tick,
                ))

        vitals_after_proc = 0
        for proc in procedures:
            has_vitals = any(
                e.type == "vitals_update" and e.tick > proc.tick
                for e in ledger
            )
            if not has_vitals:
                vitals_after_proc += 1

        if vitals_after_proc > 0:
            findings.append(TestFinding(
                severity="warn",
                message=f"{vitals_after_proc} procedure(s) have no follow-up vitals update",
            ))

        return findings
