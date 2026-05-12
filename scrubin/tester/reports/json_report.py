import json
from dataclasses import asdict
from scrubin.tester.models import TestRun


def export_json(test_run: TestRun, path="scrubin_test_report.json"):
    with open(path, "w") as f:
        json.dump(asdict(test_run), f, indent=2, default=str)
    return path
