"""Generate MCP tool modules from a FastAPI OpenAPI spec.

Usage:
    python scripts/generate_tools.py path/to/openapi.json output_dir

If output_dir is omitted it defaults to
"mcp-server/src/office_hero_mcp/tools/generated".

The script is intentionally simple; it creates a one-module-per-operation
skeleton with a Pydantic input model and a stub async function decorated
with ``@tool``.  The real HTTP call must be filled in by developers or
further improved over time.  The important part is keeping tool names and
schemas in sync with the REST API.
"""

import json
import sys
from pathlib import Path
from typing import Any


def snake_case(s: str) -> str:
    # simplistic conversion: replace hyphens with underscores
    return s.replace("-", "_")


def make_model_name(tool_name: str) -> str:
    return "".join(part.capitalize() for part in tool_name.split("_")) + "Input"


def generate(openapi_path: Path, output_dir: Path) -> None:
    spec = json.load(openapi_path.open())
    paths: dict[str, dict[str, Any]] = spec.get("paths", {})
    output_dir.mkdir(parents=True, exist_ok=True)

    for _path, methods in paths.items():
        for _method, op in methods.items():
            opid: str | None = op.get("operationId")
            if not opid:
                # skip undocumented operations
                continue
            tool_name = snake_case(opid)
            model_name = make_model_name(tool_name)
            description = op.get("description", "")

            # gather parameter names for model
            params: list[tuple[str, str]] = []
            for param in op.get("parameters", []):
                name = param.get("name")
                if not name:
                    continue
                params.append((name, "Any"))
            # request body properties (only object schemas handled)
            if "requestBody" in op:
                content = op["requestBody"].get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                if json_schema.get("type") == "object":
                    for prop, _prop_schema in json_schema.get("properties", {}).items():
                        params.append((prop, "Any"))

            # write module
            lines: list[str] = []
            lines.append("# AUTO-GENERATED from openapi spec - DO NOT EDIT")
            lines.append("from typing import Any")
            lines.append("from pydantic import BaseModel")
            lines.append("from office_hero_mcp.client import client")
            lines.append("from office_hero_mcp.server import tool\n")

            lines.append(f"class {model_name}(BaseModel):")
            if params:
                for name, typ in params:
                    lines.append(f"    {name}: {typ} | None = None")
            else:
                lines.append("    pass")
            lines.append("")
            lines.append(f'@tool(name="{tool_name}", description="{description}")')
            lines.append(f"async def {tool_name}(input: {model_name}) -> Any:")
            lines.append("    # stub implementation; replace with actual HTTP call")
            lines.append('    return await client.request("GET", "")')
            lines.append("")

            path_py = output_dir / f"{tool_name}.py"
            with path_py.open("w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"generated {path_py}")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("usage: python scripts/generate_tools.py openapi.json [output_dir]")
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
