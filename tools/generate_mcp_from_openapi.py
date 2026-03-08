r"""Generate MCP tools from a FastAPI OpenAPI spec.

This is a more capable generator than the simple one in ``scripts``; it
understands HTTP methods, path parameters, query parameters and request
bodies and produces a concrete call to ``office_hero_mcp.client`` with the
correct method, URL and payload.

Intended usage (workspace root):

    python tools/generate_mcp_from_openapi.py \
        path/to/openapi.json \
        mcp-server/src/office_hero_mcp/tools/generated

The script is deliberately "dumb" about types (all fields are typed as
``Any``) to avoid having to replicate the entire OpenAPI model machinery.  It
is run during development when the REST API is changing; the generated
modules are committed so that the MCP server can load them at runtime.
"""

import json
import sys
from pathlib import Path
from typing import Any


def snake_case(s: str) -> str:
    return s.replace("-", "_")


def make_model_name(tool_name: str) -> str:
    return "".join(part.capitalize() for part in tool_name.split("_")) + "Input"


def format_path(path_template: str, path_params: list[str]) -> str:
    # turn "/foo/{id}/bar" into f"/foo/{input.id}/bar" etc.
    result = path_template
    for p in path_params:
        result = result.replace("{" + p + "}", "{input." + p + "}")
    return result


def generate(openapi_path: Path, output_dir: Path) -> None:
    spec = json.load(openapi_path.open())
    paths: dict[str, dict[str, Any]] = spec.get("paths", {})
    output_dir.mkdir(parents=True, exist_ok=True)

    for raw_path, methods in paths.items():
        for method, op in methods.items():
            opid: str | None = op.get("operationId")
            if not opid:
                continue
            tool_name = snake_case(opid)
            model_name = make_model_name(tool_name)
            description = op.get("description", "")

            # collect parameter names and classification
            params: list[tuple[str, str]] = []
            required_params: set[str] = set()
            path_params: list[str] = []
            query_params: list[str] = []
            for param in op.get("parameters", []):
                name = param.get("name")
                if not name:
                    continue
                params.append((name, "Any"))
                if param.get("required", False):
                    required_params.add(name)
                location = param.get("in")
                if location == "path":
                    path_params.append(name)
                elif location == "query":
                    query_params.append(name)

            # handle request body
            if "requestBody" in op:
                content = op["requestBody"].get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                if json_schema.get("type") == "object":
                    required_fields = json_schema.get("required", [])
                    for prop in json_schema.get("properties", {}):
                        params.append((prop, "Any"))
                        if prop in required_fields:
                            required_params.add(prop)

            # build code
            lines: list[str] = []
            lines.append("# AUTO-GENERATED from openapi spec - DO NOT EDIT")
            lines.append("from typing import Any")
            lines.append("from pydantic import BaseModel")
            lines.append("from office_hero_mcp.client import client")
            lines.append("from office_hero_mcp.server import tool\n")

            lines.append(f"class {model_name}(BaseModel):")
            if params:
                for name, typ in params:
                    if name in required_params:
                        lines.append(f"    {name}: {typ}")
                    else:
                        lines.append(f"    {name}: {typ} | None = None")
            else:
                lines.append("    pass")
            lines.append("")

            method_upper = method.upper()
            formatted_path = format_path(raw_path, path_params)

            lines.append(f'@tool(name="{tool_name}", description="{description}")')
            lines.append(f"async def {tool_name}(input: {model_name}) -> Any:")
            # prepare call arguments
            call_args: list[str] = []
            if path_params or query_params:
                # always pass params dict; for POST/PUT we'll also send json
                call_args.append("params=input.model_dump(exclude_none=True)")
            if method_upper not in ("GET", "DELETE") and params:
                call_args.append("json=input.model_dump(exclude_none=True)")
            call_arg_str = ", ".join(call_args)

            if call_arg_str:
                lines.append(
                    f'    return await client.{method_lower(method_upper)}(f"{formatted_path}", {call_arg_str})'
                )
            else:
                lines.append(
                    f'    return await client.{method_lower(method_upper)}(f"{formatted_path}")'
                )
            lines.append("")

            path_py = output_dir / f"{tool_name}.py"
            with path_py.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"generated {path_py}")


def method_lower(m: str) -> str:
    # helper to map HTTP verb to client method name, e.g. POST -> post
    return m.lower()


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("usage: python tools/generate_mcp_from_openapi.py openapi.json [output_dir]")
        sys.exit(1)
    openapi_path = Path(argv[1])
    if not openapi_path.exists():
        print(f"spec file {openapi_path} does not exist")
        sys.exit(1)
    if len(argv) >= 3:
        out = Path(argv[2])
    else:
        out = (
            Path(__file__).parent.parent
            / "mcp-server"
            / "src"
            / "office_hero_mcp"
            / "tools"
            / "generated"
        )
    generate(openapi_path, out)


if __name__ == "__main__":
    main(sys.argv)
