from scrubin.clinical.thresholds import ClinicalThresholds
from scrubin.tester.models import TestFinding


class PhysiologyCheck:
    def __init__(self, profile=None, percentiles=None, thresholds: ClinicalThresholds = None):
        self._profile = profile
        self._thresholds_logged = False
        self._clinical = thresholds or ClinicalThresholds.defaults()

        vitals_override = {}
        profile_name = None
        if profile:
            vitals_override = getattr(profile, 'vitals_override', {})
            profile_name = getattr(profile, 'name', None)
        self._profile_name = profile_name

        if vitals_override:
            self._clinical = self._clinical.apply_patient_modifiers(vitals_override)

        t = self._clinical
        self._spo2_range = t.spo2.range_tuple()
        self._spo2_critical = t.spo2.critical_lo
        self._spo2_warning = t.spo2.warning_lo

        self._hr_range = t.heart_rate.range_tuple()
        self._hr_critical_lo = t.heart_rate.critical_lo
        self._hr_critical_hi = t.heart_rate.critical_hi

        self._bp_range = t.bp_systolic.range_tuple()
        self._bp_critical_lo = t.bp_systolic.critical_lo
        self._bp_critical_hi = t.bp_systolic.critical_hi

    def _log_thresholds(self):
        if self._thresholds_logged:
            return
        self._thresholds_logged = True
        print(f"[PhysiologyCheck] profile={self._profile_name} spo2 thresholds: critical={self._spo2_critical:.1f}, warn={self._spo2_warning:.1f}, range={self._spo2_range}")
        print(f"[PhysiologyCheck] profile={self._profile_name} hr thresholds: critical_lo={self._hr_critical_lo:.1f}, critical_hi={self._hr_critical_hi:.1f}, range={self._hr_range}")
        print(f"[PhysiologyCheck] profile={self._profile_name} bp_sys thresholds: critical_lo={self._bp_critical_lo:.1f}, critical_hi={self._bp_critical_hi:.1f}, range={self._bp_range}")

    def run(self, ledger):
        findings = []
        self._log_thresholds()

        for event in ledger:
            if event.type != "vitals_update":
                continue

            vitals = event.payload.get("vitals", {})
            if not vitals:
                continue

            spo2 = vitals.get("spo2", 100)
            if spo2 < self._clinical.spo2.absolute_floor:
                findings.append(TestFinding(
                    severity="error",
                    message="Absolute spo2 floor breached",
                    tick=event.tick,
                ))
            elif spo2 < self._spo2_critical:
                findings.append(TestFinding(
                    severity="error",
                    message="Critical hypoxia detected",
                    tick=event.tick,
                ))
            elif spo2 < self._spo2_warning:
                findings.append(TestFinding(
                    severity="warn",
                    message="Moderate hypoxia detected",
                    tick=event.tick,
                ))

            hr = vitals.get("heart_rate", 80)
            if hr < self._hr_critical_lo:
                findings.append(TestFinding(
                    severity="error",
                    message="Bradycardia critical",
                    tick=event.tick,
                ))
            elif hr > self._hr_critical_hi:
                findings.append(TestFinding(
                    severity="error",
                    message="Tachycardia critical",
                    tick=event.tick,
                ))

            sys_bp = vitals.get("bp_systolic", 120)
            if sys_bp < self._bp_critical_lo:
                findings.append(TestFinding(
                    severity="error",
                    message="Critical hypotension detected",
                    tick=event.tick,
                ))
            elif sys_bp > self._bp_critical_hi:
                findings.append(TestFinding(
                    severity="warn",
                    message="Hypertensive crisis detected",
                    tick=event.tick,
                ))

        return findings
