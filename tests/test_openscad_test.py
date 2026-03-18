"""Tests for the openscad_test package."""

import contextlib
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from openscad_test.parser import TestCase, parse_scadtest_file
from openscad_test.runner import TestResult, run_test


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def scadtest_file(content: str):
    """Write TOML content to a temporary .scadtest file.

    Yields the file path and removes the file on exit, even if the body
    raises an exception.
    """
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".scadtest", delete=False
    )
    try:
        f.write(content)
        f.close()
        yield f.name
    finally:
        if os.path.exists(f.name):
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_inline_script():
    with scadtest_file(
        """
[[test]]
name = "Inline Script Test"
script = "echo(42);"
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert len(tests) == 1
        t = tests[0]
        assert t.name == "Inline Script Test"
        assert t.script == "echo(42);"
        assert t.script_file is None
        assert t.expect_success is True
        assert t.assert_echoes == []
        assert t.assert_no_echoes is True
        assert t.assert_warnings == []
        assert t.assert_no_warnings is True


def test_parse_script_file():
    with scadtest_file(
        """
[[test]]
name = "File Test"
script_file = "my_module.scad"
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert len(tests) == 1
        t = tests[0]
        assert t.script is None
        # script_file should be resolved relative to the .scadtest file
        assert t.script_file == os.path.join(
            os.path.dirname(path), "my_module.scad"
        )


def test_parse_multiple_tests():
    with scadtest_file(
        """
[[test]]
name = "Test A"
script = "echo(1);"

[[test]]
name = "Test B"
script = "echo(2);"
expect_success = false
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert len(tests) == 2
        assert tests[0].name == "Test A"
        assert tests[0].expect_success is True
        assert tests[1].name == "Test B"
        assert tests[1].expect_success is False


def test_parse_assert_echoes():
    with scadtest_file(
        """
[[test]]
name = "Echo Assertions"
script = "echo(42);"
assert_echoes = ["ECHO: 42"]
assert_no_echoes = false
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].assert_echoes == ["ECHO: 42"]
        assert tests[0].assert_no_echoes is False


def test_parse_assert_no_echoes():
    with scadtest_file(
        """
[[test]]
name = "No Echoes"
script = "cube([1,1,1]);"
assert_no_echoes = true
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].assert_no_echoes is True


def test_parse_assert_warnings():
    with scadtest_file(
        """
[[test]]
name = "Warning Assertions"
script = "echo(1);"
assert_warnings = ["WARNING: something"]
assert_no_warnings = false
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].assert_warnings == ["WARNING: something"]
        assert tests[0].assert_no_warnings is False


def test_parse_config_timeout():
    with scadtest_file(
        """
[config]
timeout = 120

[[test]]
name = "Test A"
script = "echo(1);"

[[test]]
name = "Test B"
script = "echo(2);"
timeout = 30
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].timeout == 120  # inherits from config
        assert tests[1].timeout == 30   # per-test overrides config


def test_parse_config_expect_success():
    with scadtest_file(
        """
[config]
expect_success = false
assert_no_echoes = false
assert_no_warnings = false

[[test]]
name = "Test A"
script = "echo(1);"

[[test]]
name = "Test B"
script = "echo(2);"
expect_success = true
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].expect_success is False    # from config
        assert tests[0].assert_no_echoes is False  # from config
        assert tests[0].assert_no_warnings is False  # from config
        assert tests[1].expect_success is True     # per-test overrides config


def test_parse_timeout():
    with scadtest_file(
        """
[[test]]
name = "Timeout Test"
script = "echo(1);"
timeout = 120
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].timeout == 120


def test_parse_timeout_default():
    with scadtest_file(
        """
[[test]]
name = "Default Timeout Test"
script = "echo(1);"
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].timeout == 60


def test_parse_set_vars():
    with scadtest_file(
        """
[[test]]
name = "Set Vars"
script = "echo(w);"
set_vars = {w = 10, h = 20}
"""
    ) as path:
        tests = parse_scadtest_file(path)
        assert tests[0].set_vars == {"w": 10, "h": 20}


def test_parse_missing_script_raises():
    with scadtest_file(
        """
[[test]]
name = "Bad Test"
"""
    ) as path:
        with pytest.raises(ValueError, match="must have either 'script' or 'script_file'"):
            parse_scadtest_file(path)


def test_parse_both_script_and_script_file_raises():
    with scadtest_file(
        """
[[test]]
name = "Bad Test"
script = "echo(1);"
script_file = "foo.scad"
"""
    ) as path:
        with pytest.raises(ValueError, match="not both"):
            parse_scadtest_file(path)


def test_parse_empty_file():
    with scadtest_file("") as path:
        tests = parse_scadtest_file(path)
        assert tests == []


# ---------------------------------------------------------------------------
# Runner tests (using mocks to avoid requiring OpenSCAD)
# ---------------------------------------------------------------------------


def _make_mock_runner(success=True, echos=None, warnings=None, errors=None):
    """Return a mock OpenScadRunner instance with the given attributes."""
    mock = MagicMock()
    mock.run.return_value = success
    mock.success = success
    mock.echos = echos or []
    mock.warnings = warnings or []
    mock.errors = errors or []
    return mock


def _make_test_case(**kwargs):
    defaults = dict(
        name="Test",
        script="echo(1);",
        script_file=None,
        timeout=60,
        set_vars={},
        expect_success=True,
        assert_echoes=[],
        assert_no_echoes=True,
        assert_warnings=[],
        assert_no_warnings=True,
    )
    defaults.update(kwargs)
    return TestCase(**defaults)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_passes_on_success(MockRunner):
    MockRunner.return_value = _make_mock_runner(success=True)
    tc = _make_test_case(expect_success=True)
    result = run_test(tc)
    assert result.passed is True
    assert result.messages == []


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_fails_when_expected_success_but_got_error(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=False, errors=["ERROR: something went wrong"]
    )
    tc = _make_test_case(expect_success=True)
    result = run_test(tc)
    assert result.passed is False
    assert any("ERROR:" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_passes_when_expected_failure_and_got_error(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=False, errors=["ERROR: expected failure"]
    )
    tc = _make_test_case(expect_success=False)
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_fails_when_expected_failure_but_succeeded(MockRunner):
    MockRunner.return_value = _make_mock_runner(success=True)
    tc = _make_test_case(expect_success=False)
    result = run_test(tc)
    assert result.passed is False
    assert any("Expected test to fail" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_echoes_passes(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, echos=["ECHO: 42"]
    )
    tc = _make_test_case(assert_echoes=["ECHO: 42"])
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_echoes_substring_match(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, echos=["ECHO: \"hello world\""]
    )
    tc = _make_test_case(assert_echoes=["hello"])
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_echoes_fails(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, echos=["ECHO: 99"]
    )
    tc = _make_test_case(assert_echoes=["ECHO: 42"])
    result = run_test(tc)
    assert result.passed is False
    assert any("Expected echo not found" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_no_echoes_passes(MockRunner):
    MockRunner.return_value = _make_mock_runner(success=True, echos=[])
    tc = _make_test_case(assert_no_echoes=True)
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_no_echoes_fails(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, echos=["ECHO: unexpected"]
    )
    tc = _make_test_case(assert_no_echoes=True)
    result = run_test(tc)
    assert result.passed is False
    assert any("Expected no echoes" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_warnings_passes(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, warnings=["WARNING: something"]
    )
    tc = _make_test_case(assert_warnings=["WARNING: something"])
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_warnings_fails(MockRunner):
    MockRunner.return_value = _make_mock_runner(success=True, warnings=[])
    tc = _make_test_case(assert_warnings=["WARNING: expected"])
    result = run_test(tc)
    assert result.passed is False
    assert any("Expected warning not found" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_no_warnings_passes(MockRunner):
    MockRunner.return_value = _make_mock_runner(success=True, warnings=[])
    tc = _make_test_case(assert_no_warnings=True)
    result = run_test(tc)
    assert result.passed is True


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_assert_no_warnings_fails(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=True, warnings=["WARNING: unexpected"]
    )
    tc = _make_test_case(assert_no_warnings=True)
    result = run_test(tc)
    assert result.passed is False
    assert any("Expected no warnings" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_timeout(MockRunner):
    import time

    def slow_run():
        time.sleep(5)

    mock = MagicMock()
    mock.run.side_effect = slow_run
    MockRunner.return_value = mock

    tc = _make_test_case(timeout=1)
    result = run_test(tc)
    assert result.passed is False
    assert any("timed out" in m for m in result.messages)


@patch("openscad_test.runner.OpenScadRunner")
def test_run_test_includes_echoes_and_warnings_in_failure_messages(MockRunner):
    MockRunner.return_value = _make_mock_runner(
        success=False,
        echos=["ECHO: some output"],
        warnings=["WARNING: something"],
        errors=["ERROR: fatal"],
    )
    tc = _make_test_case(expect_success=True)
    result = run_test(tc)
    assert result.passed is False
    assert "ECHO: some output" in result.messages
    assert "WARNING: something" in result.messages
    assert "ERROR: fatal" in result.messages


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


@patch("openscad_test.runner.OpenScadRunner")
def test_main_all_pass(MockRunner, capsys):
    MockRunner.return_value = _make_mock_runner(success=True)
    with scadtest_file(
        """
[[test]]
name = "Pass Test"
script = "echo(1);"
"""
    ) as path:
        import sys
        from openscad_test.main import main

        sys.argv = ["openscad-test", "-j", "1", path]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Pass Test PASSED" in captured.out
        assert "1 of 1 tests passed, 0 failed." in captured.out


@patch("openscad_test.runner.OpenScadRunner")
def test_main_some_fail(MockRunner, capsys):
    MockRunner.return_value = _make_mock_runner(
        success=False, errors=["ERROR: oops"]
    )
    with scadtest_file(
        """
[[test]]
name = "Fail Test"
script = "bad_code();"
expect_success = true
"""
    ) as path:
        import sys
        from openscad_test.main import main

        sys.argv = ["openscad-test", "-j", "1", path]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Fail Test FAILED" in captured.out
        assert "0 of 1 tests passed, 1 failed." in captured.out


@patch("openscad_test.runner.OpenScadRunner")
def test_main_no_args(MockRunner, capsys):
    import sys
    from openscad_test.main import main

    sys.argv = ["openscad-test"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.out
