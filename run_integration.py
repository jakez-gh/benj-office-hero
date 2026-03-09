import pytest

# run the integration tests programmatically
result = pytest.main(["tests/test_generate_mcp_integration.py", "-q"])
print("pytest exit code", result)
