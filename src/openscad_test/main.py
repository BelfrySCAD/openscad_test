"""Command-line entry point for openscad-test."""

import sys

from .parser import parse_scadtest_file
from .runner import run_test


def main():
    """Run OpenSCAD tests defined in one or more .scadtest files.

    Usage::

        openscad-test <file.scadtest> [file2.scadtest ...]

    For each test in each file, prints the test name followed by ``PASSED``
    or ``FAILED``.  When a test fails, any ECHO, WARNING, or ERROR messages
    from OpenSCAD are printed beneath the ``FAILED`` line.

    After all tests have run, a summary line is printed showing how many
    tests passed and how many failed.  The process exits with code ``0`` if
    all tests passed, or ``1`` if any test failed.
    """
    args = sys.argv[1:]

    if not args:
        print("Usage: openscad-test <file.scadtest> [file2.scadtest ...]")
        sys.exit(1)

    passed = 0
    failed = 0

    for filepath in args:
        try:
            tests = parse_scadtest_file(filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}", file=sys.stderr)
            sys.exit(1)

        print(filepath)
        file_passed = 0
        file_failed = 0

        for test_case in tests:
            result = run_test(test_case)
            if result.passed:
                print(f"  {test_case.name} PASSED")
                file_passed += 1
                passed += 1
            else:
                print(f"  {test_case.name} FAILED")
                for msg in result.messages:
                    print(f"    {msg}")
                file_failed += 1
                failed += 1

        file_total = file_passed + file_failed
        print(f"  {file_passed} of {file_total} passed, {file_failed} failed.")
        print()

    total = passed + failed
    print(f"{passed} of {total} tests passed, {failed} failed.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
