from scrubin.tester.models import TestRun


def print_report(test_run: TestRun):
    print("\n" + "=" * 55)
    print("  SCRUBIN TEST REPORT")
    print("=" * 55)
    print(f"  Seed:         {test_run.seed}")
    print(f"  Ticks:        {test_run.ticks}")
    print(f"  Ledger size:  {test_run.ledger_size}")
    print(f"  Score:        {test_run.score}/100")
    print("-" * 55)

    errors = [f for f in test_run.findings if f.severity == "error"]
    warns = [f for f in test_run.findings if f.severity == "warn"]
    infos = [f for f in test_run.findings if f.severity == "info"]

    print(f"  Findings: {len(test_run.findings)} total")
    print(f"    errors: {len(errors)}")
    print(f"    warns:  {len(warns)}")
    print(f"    infos:  {len(infos)}")

    if errors:
        print("\n  ERRORS:")
        for f in errors:
            tick_str = f" (tick {f.tick})" if f.tick is not None else ""
            print(f"    - {f.message}{tick_str}")

    if warns:
        print("\n  WARNINGS:")
        for f in warns:
            tick_str = f" (tick {f.tick})" if f.tick is not None else ""
            print(f"    - {f.message}{tick_str}")

    if infos:
        print("\n  INFO:")
        for f in infos:
            tick_str = f" (tick {f.tick})" if f.tick is not None else ""
            print(f"    - {f.message}{tick_str}")

    print("=" * 55 + "\n")
