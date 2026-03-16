# openscad_test

A testing framework for OpenSCAD scripts, built with [uv](https://github.com/astral-sh/uv) and available on [PyPI](https://pypi.org/).

## Installation

```bash
pip install openscad-test
```

## Requirements

- Python 3.11 or later
- [OpenSCAD](https://openscad.org/) installed and available on your system `PATH`

## Usage

Create one or more `.scadtest` files describing your tests, then run:

```bash
openscad-test mymodule.scadtest
```

You can pass multiple files at once:

```bash
openscad-test tests/basic.scadtest tests/advanced.scadtest
```

### Output

Each test prints its name followed by `PASSED` or `FAILED`.  When a test
fails, the relevant ECHO, WARNING, and ERROR lines from OpenSCAD are shown.
After all tests have run, a summary is printed:

```
Echo Integer Test PASSED
Expected Failure Test PASSED
No Warnings Test PASSED
Bad Echo Test FAILED
  Expected echo not found: ECHO: 99
  ECHO: 42

3 of 4 tests passed, 1 failed.
```

The process exits with code `0` if all tests pass, or `1` if any test fails.

## The `.scadtest` File Format

A `.scadtest` file is a [TOML](https://toml.io/) file.  Each test is defined
as a `[[test]]` section.

### Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | `"Unnamed Test"` | Human-readable test name |
| `script` | string | — | Inline OpenSCAD script to run |
| `script_file` | string | — | Path to a `.scad` file (relative to the `.scadtest` file) |
| `set_vars` | table | `{}` | Variables to pass to the script via `-D` |
| `expect_success` | bool | `true` | Whether OpenSCAD should complete without errors |
| `assert_echoes` | list of strings | `[]` | Each string must appear (as a substring) in an ECHO output line |
| `assert_no_echoes` | bool | `true` | Assert that there are no ECHO output lines (skipped when `assert_echoes` is non-empty) |
| `assert_warnings` | list of strings | `[]` | Each string must appear (as a substring) in a WARNING line |
| `assert_no_warnings` | bool | `true` | Assert that there are no WARNING lines (skipped when `assert_warnings` is non-empty) |

Exactly one of `script` or `script_file` must be provided for each test.

### Example

```toml
[[test]]
# A test that should succeed and produce a specific echo.
name = "Echo Integer Test"
script = "echo(42);"
expect_success = true
assert_echoes = ["ECHO: 42"]

[[test]]
# Pass variables into the script using set_vars.
name = "Set Vars Test"
script = "echo(w);"
set_vars = {w = 10}
expect_success = true
assert_echoes = ["ECHO: 10"]

[[test]]
# A test that expects OpenSCAD to report an error.
# Set assert_no_echoes/assert_no_warnings to false for expected-failure tests
# since OpenSCAD may emit warnings before failing.
name = "Expected Failure Test"
script = "this_function_does_not_exist();"
expect_success = false
assert_no_echoes = false
assert_no_warnings = false

[[test]]
# A test using an external .scad file with no echoes or warnings.
# assert_no_echoes and assert_no_warnings are true by default.
name = "No Warnings Test"
script_file = "my_module.scad"
expect_success = true
```

## Python API

You can also use `openscad_test` programmatically:

```python
from openscad_test import parse_scadtest_file, run_test

tests = parse_scadtest_file("mymodule.scadtest")
for test_case in tests:
    result = run_test(test_case)
    if result.passed:
        print(f"{test_case.name} PASSED")
    else:
        print(f"{test_case.name} FAILED")
        for msg in result.messages:
            print(f"  {msg}")
```

## License

MIT
