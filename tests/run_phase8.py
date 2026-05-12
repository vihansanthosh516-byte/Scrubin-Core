import sys
import traceback

_passed = 0
_failed = 0
_errors = []


def _run_test(name, fn):
    global _passed, _failed
    try:
        fn()
        _passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        _failed += 1
        _errors.append((name, e))
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()


def run_all():
    from tests.test_contracts import TESTS as t1
    from tests.test_replay import TESTS as t2
    from tests.test_audit import TESTS as t3
    from tests.test_perf import TESTS as t4
    from tests.test_integration import TESTS as t5

    all_tests = t1 + t2 + t3 + t4 + t5
    print(f"\nRunning {len(all_tests)} Phase 8 tests...\n")
    for name, fn in all_tests:
        _run_test(name, fn)

    print(f"\n{'='*60}")
    print(f"Results: {_passed} passed, {_failed} failed out of {_passed + _failed}")
    if _errors:
        print("\nFailures:")
        for name, e in _errors:
            print(f"  - {name}: {e}")
    return _failed == 0


if __name__ == "__main__":
    sys.path.insert(0, "/home/vihan/repos/scrubin-core")
    ok = run_all()
    sys.exit(0 if ok else 1)
