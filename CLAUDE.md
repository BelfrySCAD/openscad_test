# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_openscad_test.py::TestClassName::test_name

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Build distribution
uv build
```

## Architecture

This is a Python CLI tool (`openscad-test`) and library for testing OpenSCAD scripts. It has three core modules:

- **`src/openscad_test/parser.py`** — Parses `.scadtest` TOML files into `TestCase` dataclasses. Validates that exactly one of `script` (inline) or `script_file` (path relative to the `.scadtest` file) is provided per test.

- **`src/openscad_test/runner.py`** — Executes `TestCase` objects using `OpenScadRunner` (from the `openscad-runner` PyPI package) in `test_only` render mode. Inline scripts are written to a temp `.scad` file, run, then deleted. Returns `TestResult` with pass/fail and failure messages.

- **`src/openscad_test/main.py`** — CLI entry point. Parses files, runs tests, prints per-test PASSED/FAILED output (with ECHO/WARNING/ERROR lines on failure), and exits 0/1.

Public API (`__init__.py`) exports: `TestCase`, `TestResult`, `parse_scadtest_file`, `run_test`.

## Testing Approach

Tests mock `OpenScadRunner` — actual OpenSCAD installation is not required to run the test suite. The mock returns configurable `succeeded`, `echoes`, `warnings`, and `errors` values. A `scadtest_file()` context manager helper creates temporary `.scadtest` TOML files.

## Publishing

Tagged releases (`v*.*.*`) trigger `.github/workflows/publish.yml`, which builds and publishes to PyPI using OIDC Trusted Publishing (no API token needed).
