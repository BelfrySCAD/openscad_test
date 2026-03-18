"""Parse .scadtest TOML files into TestCase objects."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestCase:
    """Represents a single OpenSCAD test case."""

    name: str
    script: Optional[str]
    script_file: Optional[str]
    script_dir: Optional[str] = None
    timeout: int = 60
    set_vars: dict = field(default_factory=dict)
    expect_success: bool = True
    assert_echoes: list = field(default_factory=list)
    assert_no_echoes: bool = True
    assert_warnings: list = field(default_factory=list)
    assert_no_warnings: bool = True


def parse_scadtest_file(filepath: str) -> list[TestCase]:
    """Parse a .scadtest TOML file and return a list of TestCase objects.

    A .scadtest file is a TOML file containing one or more [[test]] sections.
    Each [[test]] section defines a single OpenSCAD test case.

    Example::

        [[test]]
        name = "Basic Echo Test"
        script = "echo(42);"
        expect_success = true
        assert_echoes = ["ECHO: 42"]

        [[test]]
        name = "External File Test"
        script_file = "my_module.scad"
        expect_success = true

    Args:
        filepath: Path to the .scadtest file.

    Returns:
        A list of TestCase objects.

    Raises:
        ValueError: If a test is missing both ``script`` and ``script_file``,
            or if a test has both.
        FileNotFoundError: If the file does not exist.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    path = Path(filepath)
    with open(path, "rb") as f:
        data = tomllib.load(f)

    config = data.get("config", {})

    def cfg(key, hardcoded_default):
        return config.get(key, hardcoded_default)

    tests = []
    for test_data in data.get("test", []):
        name = test_data.get("name", "Unnamed Test")
        script = test_data.get("script")
        script_file = test_data.get("script_file")

        if script is None and script_file is None:
            raise ValueError(
                f"Test '{name}' must have either 'script' or 'script_file'."
            )
        if script is not None and script_file is not None:
            raise ValueError(
                f"Test '{name}' must have either 'script' or 'script_file', not both."
            )

        if script_file is not None:
            # Resolve script_file relative to the directory of the .scadtest file
            script_file = str(path.parent / script_file)

        test = TestCase(
            name=name,
            script=script,
            script_file=script_file,
            script_dir=str(path.parent),
            timeout=test_data.get("timeout", cfg("timeout", 60)),
            set_vars=test_data.get("set_vars", {}),
            expect_success=test_data.get("expect_success", cfg("expect_success", True)),
            assert_echoes=test_data.get("assert_echoes", []),
            assert_no_echoes=test_data.get("assert_no_echoes", cfg("assert_no_echoes", True)),
            assert_warnings=test_data.get("assert_warnings", []),
            assert_no_warnings=test_data.get("assert_no_warnings", cfg("assert_no_warnings", True)),
        )
        tests.append(test)

    return tests
