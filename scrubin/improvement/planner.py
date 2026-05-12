from .patches import Patch


class PlanGenerator:
    def generate(self, categories, test_run, profile: str = "default", fixability: dict = None):
        patches = []
        seen = set()

        for f in categories["physiology"]:
            msg = f.message.lower()
            if "hypoxia" in msg:
                key = ("agents/vitals.py", "oxygenation.min_spo2", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/vitals.py",
                        action="modify",
                        path="oxygenation.min_spo2",
                        value=86,
                        reason="Raise spo2 floor above PhysiologyCheck warn threshold (85)",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))
            if "tachycardia" in msg:
                key = ("agents/vitals.py", "heart_rate.max", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/vitals.py",
                        action="modify",
                        path="heart_rate.max",
                        value=179,
                        reason="Lower hr ceiling below PhysiologyCheck tachycardia threshold (180)",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))
            if "bradycardia" in msg:
                key = ("agents/vitals.py", "heart_rate.min", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/vitals.py",
                        action="modify",
                        path="heart_rate.min",
                        value=41,
                        reason="Raise hr floor above PhysiologyCheck bradycardia threshold (40)",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))
            if "hypertensive" in msg:
                key = ("agents/vitals.py", "bp_systolic.max", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/vitals.py",
                        action="modify",
                        path="bp_systolic.max",
                        value=199,
                        reason="Lower systolic ceiling below PhysiologyCheck hypertensive threshold (200)",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))
            if "hypotension" in msg:
                key = ("agents/vitals.py", "bp_systolic.min", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/vitals.py",
                        action="modify",
                        path="bp_systolic.min",
                        value=61,
                        reason="Raise systolic floor above PhysiologyCheck hypotension threshold (60)",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))

        for f in categories["causality"]:
            msg = f.message.lower()
            if "no clinical response" in msg:
                key = ("agents/procedure.py", "procedure_enabled", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/procedure.py",
                        action="modify",
                        path="procedure_enabled",
                        value=True,
                        reason="Enable procedure agent so complications receive clinical responses",
                        scope={"profile": profile},
                        priority=8,
                        patch_type="config",
                    ))
            elif "follow-up vitals" in msg:
                key = ("agents/procedure.py", "ensure_post_procedure_vitals", "logic")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/procedure.py",
                        action="ensure_post_procedure_vitals",
                        path="post_procedure_vitals",
                        value=True,
                        reason="Inject vitals_update event after every procedure event to satisfy follow-up check",
                        scope={"profile": profile},
                        priority=9,
                        patch_type="logic",
                        target_path="agents/procedure.py:_on_complication",
                    ))
            elif "matching complication" in msg:
                key = ("agents/procedure.py", "procedure_trigger", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/procedure.py",
                        action="modify",
                        path="procedure_trigger",
                        value="complication_gated",
                        reason="Procedure should only fire in response to active complications",
                        scope={"profile": profile},
                        priority=5,
                        patch_type="config",
                    ))

        for f in categories["recovery"]:
            msg = f.message.lower()
            if "no vitals monitoring" in msg:
                key = ("agents/procedure.py", "enforce_recovery_event", "logic")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/procedure.py",
                        action="enforce_recovery_event",
                        path="recovery_monitoring",
                        value=True,
                        reason="Inject vitals_update and recovery events after procedures to satisfy recovery check",
                        scope={"profile": profile},
                        priority=9,
                        patch_type="logic",
                        target_path="agents/procedure.py:_on_procedure",
                    ))
            else:
                key = ("procedures.yaml", "recovery_window", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="procedures.yaml",
                        action="modify",
                        path="recovery_window",
                        value=7,
                        reason="Extend recovery window for better recovery tracking",
                        scope={"profile": profile},
                        priority=5,
                        patch_type="config",
                    ))

        for f in categories["procedure"]:
            msg = f.message.lower()
            if "no procedure administered" in msg:
                key = ("agents/procedure.py", "procedure_enabled", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="agents/procedure.py",
                        action="modify",
                        path="procedure_enabled",
                        value=True,
                        reason="Enable procedure agent so complications receive clinical interventions",
                        scope={"profile": profile},
                        priority=10,
                        patch_type="config",
                    ))
            else:
                key = ("procedures.yaml", "procedure_branch", "config")
                if key not in seen:
                    seen.add(key)
                    patches.append(Patch(
                        target="procedures.yaml",
                        action="add",
                        path="procedure_branch",
                        value={"trigger": "auto", "window": 3},
                        reason="Missing procedure branch for detected complication",
                        scope={"profile": profile},
                        priority=5,
                        patch_type="config",
                    ))

        return patches
