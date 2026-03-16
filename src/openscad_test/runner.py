"""Run OpenSCAD test cases and collect results."""

import os
import tempfile
from dataclasses import dataclass, field

from openscad_runner import OpenScadRunner, RenderMode

from .parser import TestCase


@dataclass
class TestResult:
    """The result of running a single OpenSCAD test case."""

    test_case: TestCase
    passed: bool
    messages: list = field(default_factory=list)


def run_test(test_case: TestCase) -> TestResult:
    """Run a single OpenSCAD test case and return its result.

    The test is run using :class:`openscad_runner.OpenScadRunner` in
    ``test_only`` mode so that no output file is generated.

    A test passes when all of the following are true:

    - If ``expect_success`` is ``True``, OpenSCAD reported no errors.
    - If ``expect_success`` is ``False``, OpenSCAD reported at least one error.
    - All strings in ``assert_echoes`` are found (as substrings) in the ECHO
      output lines produced by OpenSCAD.
    - If ``assert_no_echoes`` is ``True`` and ``assert_echoes`` is empty,
      there are no ECHO output lines.
    - All strings in ``assert_warnings`` are found (as substrings) in the
      WARNING output lines produced by OpenSCAD.
    - If ``assert_no_warnings`` is ``True`` and ``assert_warnings`` is empty,
      there are no WARNING lines.

    When a test fails, relevant ECHO, WARNING, and ERROR lines from OpenSCAD
    are included in :attr:`TestResult.messages`.

    Args:
        test_case: The test case to run.

    Returns:
        A :class:`TestResult` describing whether the test passed and any
        failure messages.
    """
    tmp_file = None
    try:
        if test_case.script is not None:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".scad", delete=False
            ) as f:
                f.write(test_case.script)
                tmp_file = f.name
            script_file = tmp_file
        else:
            script_file = test_case.script_file

        runner = OpenScadRunner(
            scriptfile=script_file,
            outfile="test_output.term",
            render_mode=RenderMode.test_only,
            set_vars=test_case.set_vars,
        )
        runner.run()

        passed = True
        messages = []

        # Check expect_success
        if test_case.expect_success and not runner.success:
            passed = False
            messages.extend(runner.echos)
            messages.extend(runner.warnings)
            messages.extend(runner.errors)
        elif not test_case.expect_success and runner.success:
            passed = False
            messages.append("Expected test to fail, but it succeeded.")

        if passed:
            # Check assert_echoes
            for expected in test_case.assert_echoes:
                if not any(expected in echo for echo in runner.echos):
                    passed = False
                    messages.append(f"Expected echo not found: {expected}")
                    messages.extend(runner.echos)
                    break

            # Check assert_no_echoes (skipped when assert_echoes lists specific
            # expected echoes, since the two checks would contradict each other)
            if test_case.assert_no_echoes and not test_case.assert_echoes and runner.echos:
                passed = False
                messages.append("Expected no echoes, but got:")
                messages.extend(runner.echos)

            # Check assert_warnings
            for expected in test_case.assert_warnings:
                if not any(expected in warning for warning in runner.warnings):
                    passed = False
                    messages.append(f"Expected warning not found: {expected}")
                    messages.extend(runner.warnings)
                    break

            # Check assert_no_warnings (skipped when assert_warnings lists specific
            # expected warnings, since the two checks would contradict each other)
            if test_case.assert_no_warnings and not test_case.assert_warnings and runner.warnings:
                passed = False
                messages.append("Expected no warnings, but got:")
                messages.extend(runner.warnings)

        return TestResult(test_case=test_case, passed=passed, messages=messages)

    finally:
        if tmp_file is not None and os.path.exists(tmp_file):
            os.unlink(tmp_file)
