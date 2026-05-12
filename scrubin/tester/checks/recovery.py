from scrubin.tester.models import TestFinding
from scrubin.core.config import ConfigLayer


class RecoveryCheck:
    def __init__(self, config: ConfigLayer = None):
        self._config = config or ConfigLayer()

    def run(self, ledger):
        findings = []
        recovery_window = self._config.get("procedures.yaml", "recovery_window", 5)

        complications = [e for e in ledger if e.type == "complication"]

        for comp in complications:
            comp_tick = comp.tick
            comp_name = comp.payload.get("complication", "unknown")
            end_tick = comp_tick + recovery_window

            vitals_in_window = [
                e for e in ledger
                if e.type == "vitals_update"
                and comp_tick < e.tick <= end_tick
            ]

            if not vitals_in_window:
                findings.append(TestFinding(
                    severity="warn",
                    message=f"No vitals monitoring after '{comp_name}' at tick {comp_tick} within recovery window",
                    tick=comp_tick,
                ))

            procedures_for_comp = [
                e for e in ledger
                if e.type == "procedure"
                and e.payload.get("target") == comp_name
                and comp_tick <= e.tick <= end_tick
            ]

            if not procedures_for_comp:
                findings.append(TestFinding(
                    severity="error",
                    message=f"No procedure administered for '{comp_name}' within recovery window",
                    tick=comp_tick,
                ))

        return findings
