import importlib
import os
import pkgutil

from mcp.server.fastmcp import FastMCP

# create singleton server instance that tools can decorate
# read host/port from environment so the server can be started on custom
# addresses during tests or deployments.
host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
port = int(os.getenv("MCP_SERVER_PORT", "8000"))
server = FastMCP(name="office-hero-mcp", host=host, port=port)


def load_tools() -> None:
    """Import every module under tools/generated and tools/custom to register them."""
    from office_hero_mcp import tools

    for pkg in (tools.generated, tools.custom):
        for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{name}")


# convenience alias used by generator
tool = server.tool
