from .classifier import classify_findings
from .planner import PlanGenerator


class ImprovementEngine:
    def analyze(self, test_run, profile: str = "default"):
        categories, fixability = classify_findings(test_run.findings)
        planner = PlanGenerator()
        patches = planner.generate(categories, test_run, profile=profile, fixability=fixability)

        return {
            "score": test_run.score,
            "root_causes": {
                k: [f.message for f in v]
                for k, v in categories.items()
                if v
            },
            "fixability": {
                k: [f.message for _, f in v]
                for k, v in fixability.items()
                if v
            },
            "patches": patches,
        }
