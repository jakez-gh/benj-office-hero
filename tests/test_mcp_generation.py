import json
import sys

from scripts import generate_tools


def test_generate_tools_creates_python_modules(tmp_path, monkeypatch):
    # create a minimal OpenAPI spec with one operation
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/customers": {
                "get": {
                    "operationId": "get_customers",
                    "description": "List customers",
                    "parameters": [
                        {
                            "name": "search",
                            "in": "query",
                            "schema": {"type": "string"},
                        }
                    ],
                }
            }
        },
    }
    spec_file = tmp_path / "openapi.json"
    spec_file.write_text(json.dumps(spec))

    out_dir = tmp_path / "generated"
    # call the generator directly
    generate_tools.generate(spec_file, out_dir)

    generated_file = out_dir / "get_customers.py"
    assert generated_file.exists(), "Expected module to be generated"
    content = generated_file.read_text()
    # basic sanity checks
    assert "class GetCustomersInput" in content
    assert "search" in content
    assert '@tool(name="get_customers"' in content

    # import the module dynamically to ensure it's valid Python
    sys.path.insert(0, str(out_dir))
    try:
        imported = __import__("get_customers")
        assert hasattr(imported, "get_customers")
        assert hasattr(imported, "GetCustomersInput")
    finally:
        sys.path.pop(0)


def test_generator_handles_request_body(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/jobs": {
                "post": {
                    "operationId": "create_job",
                    "description": "Create a job",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"title": {"type": "string"}},
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    spec_file = tmp_path / "openapi.json"
    spec_file.write_text(json.dumps(spec))
    out_dir = tmp_path / "generated2"
    generate_tools.generate(spec_file, out_dir)
    gen = (out_dir / "create_job.py").read_text()
    assert "title" in gen
