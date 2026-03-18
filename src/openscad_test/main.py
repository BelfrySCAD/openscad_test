"""Command-line entry point for openscad-test."""

import argparse
import concurrent.futures
import sys

from .parser import parse_scadtest_file
from .runner import run_test


def main():
    """Run OpenSCAD tests defined in one or more .scadtest files.

    Usage::

        openscad-test [-j N] <file.scadtest> [file2.scadtest ...]

    For each test in each file, prints the test name followed by ``PASSED``
    or ``FAILED``.  When a test fails, any ECHO, WARNING, or ERROR messages
    from OpenSCAD are printed beneath the ``FAILED`` line.

    After all tests have run, a summary line is printed showing how many
    tests passed and how many failed.  The process exits with code ``0`` if
    all tests passed, or ``1`` if any test failed.
    """
    parser = argparse.ArgumentParser(
        prog="openscad-test",
        description="Run OpenSCAD tests defined in .scadtest files.",
    )
    parser.add_argument("files", nargs="*", metavar="file.scadtest")
    parser.add_argument(
        "-j", "--jobs",
        type=int, default=5, metavar="N",
        help="Number of parallel test processes (default: 5)",
    )
    args = parser.parse_args()

    if not args.files:
        print("Usage: openscad-test [-j N] <file.scadtest> [file2.scadtest ...]")
        sys.exit(1)

    passed = 0
    failed = 0
    failed_names = []

    for filepath in args.files:
        try:
            tests = parse_scadtest_file(filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}", file=sys.stderr)
            sys.exit(1)

        print(filepath)
        file_passed = 0
        file_failed = 0

        if args.jobs == 1 or len(tests) <= 1:
            results = [run_test(tc) for tc in tests]
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as executor:
                results = list(executor.map(run_test, tests))

        for result in results:
            if result.passed:
                print(f"  {result.test_case.name} PASSED")
                file_passed += 1
                passed += 1
            else:
                print(f"  {result.test_case.name} FAILED")
                for msg in result.messages:
                    print(f"    {msg}")
                file_failed += 1
                failed += 1
                failed_names.append((filepath, result.test_case.name))

        file_total = file_passed + file_failed
        print(f"  {file_passed} of {file_total} passed, {file_failed} failed.")
        print()

    total = passed + failed
    print(f"{passed} of {total} tests passed, {failed} failed.")
    if failed_names:
        print("\nFailed tests:")
        for filepath, name in failed_names:
            print(f"  {filepath}: {name}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
