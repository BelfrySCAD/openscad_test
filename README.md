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

By default, up to 5 tests run in parallel.  Use `-j` to control the number
of parallel processes:

```bash
openscad-test -j 1 mymodule.scadtest   # serial
openscad-test -j 8 mymodule.scadtest   # up to 8 parallel
```

### Output

Each file is listed as a header, with individual test results indented beneath
it.  When a test fails, the relevant ECHO, WARNING, and ERROR lines from
OpenSCAD are shown.  A per-file summary is printed after each file, followed
by an overall summary:

```
tests/basic.scadtest
  Echo Integer Test PASSED
  Expected Failure Test PASSED
  No Warnings Test PASSED
  Bad Echo Test FAILED
    Expected echo not found: ECHO: 99
    ECHO: 42
  3 of 4 passed, 1 failed.

2 of 4 tests passed, 1 failed.
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
| `timeout` | integer | `60` | Maximum seconds to wait for the test to complete before marking it failed |

Exactly one of `script` or `script_file` must be provided for each test.

### File-level configuration

A `[config]` section at the top of the file sets default values for all tests
in that file.  Per-test values always take precedence over `[config]` values,
which in turn take precedence over the built-in defaults.

The following fields are supported in `[config]`:

| Field | Description |
|---|---|
| `timeout` | Default timeout in seconds for all tests (built-in default: `60`) |
| `expect_success` | Default for `expect_success` (built-in default: `true`) |
| `assert_no_echoes` | Default for `assert_no_echoes` (built-in default: `true`) |
| `assert_no_warnings` | Default for `assert_no_warnings` (built-in default: `true`) |

```toml
[config]
timeout = 120
expect_success = false
assert_no_echoes = false
assert_no_warnings = false

[[test]]
# inherits all config defaults above
name = "Expected Failure Test"
script = "this_function_does_not_exist();"

[[test]]
# per-test value overrides config
name = "Should Succeed"
script = "echo(1);"
expect_success = true
timeout = 30
```

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
