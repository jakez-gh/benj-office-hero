import re
import sys
from pathlib import Path

import toml


def test_python_version_matches_adr():
    """ADR 057 mandates Python 3.11+. This test enforces it at runtime and config.

    - the interpreter running pytest must be >= 3.11
    - pyproject.toml `requires-python` field must declare the same constraint
    - Dockerfile base image should be `python:3.11` or newer
    """
    # runtime check
    assert sys.version_info >= (3, 11), (
        f"Python {sys.version_info.major}.{sys.version_info.minor} is too old; "
        "ADR 057 requires 3.11+."
    )

    # pyproject check
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    data = toml.loads(pyproject.read_text())
    requires = data.get("project", {}).get("requires-python", "")
    assert requires, "pyproject.toml must specify requires-python"
    assert re.search(
        r"3\.11", requires
    ), "pyproject.toml requires-python should include '3.11' per ADR057"

    # Dockerfile check (if the repo has one)
    dockerfile = Path(__file__).parent.parent / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text()
        assert "python:3.11" in text, "Dockerfile must use python:3.11 base image"


# future hooks for other ADRs can be added here; example:
# def test_adr_063_logging_compliance():
#     ...
