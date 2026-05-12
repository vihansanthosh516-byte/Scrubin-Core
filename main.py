from scrubin.tester.runner import TestRunner
from scrubin.tester.reports.console import print_report
from scrubin.improvement.engine import ImprovementEngine
from scrubin.improvement.executor import PatchExecutor
from scrubin.improvement.diff_renderer import render_patch_plan


def main():
    profiles = ["default", "hypoxia", "broken_procedure", "recovery_suppression", "causality_race"]

    for profile_name in profiles:
        print(f"\n{'=' * 60}")
        print(f"  PROFILE: {profile_name}")
        print(f"{'=' * 60}")

        runner = TestRunner(seed=42, ticks=10, profile=profile_name)
        test_run = runner.run()
        print_report(test_run)

        engine = ImprovementEngine()
        analysis = engine.analyze(test_run, profile=profile_name)

        print(f"  Root causes: {analysis['root_causes'] or 'none'}")
        print(f"  Patches generated: {len(analysis['patches'])}")

        if analysis["patches"]:
            print(f"\n{render_patch_plan(analysis['patches'])}")

            executor = PatchExecutor()
            result = executor.apply_and_rerun(test_run, analysis["patches"], profile=profile_name)
            print(f"\n  PATCH EXECUTION:")
            print(f"    Before score:  {result['before_score']}/100")
            print(f"    After score:   {result['after_score']}/100")
            print(f"    Delta:         +{result['delta']}")
            print(f"    Patches applied: {result['applied_patches']}")
            print(f"    Remaining findings: {result['remaining_findings']}")
            print(f"    Remaining patches: {result['remaining_patches']}")
        else:
            print("  No patches required. System is healthy.")


if __name__ == "__main__":
    main()
