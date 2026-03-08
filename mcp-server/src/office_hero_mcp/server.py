import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP

# create singleton server instance that tools can decorate
server = FastMCP(name="office-hero-mcp")


def load_tools() -> None:
    """Import every module under tools/generated and tools/custom to register them."""
    from office_hero_mcp import tools

    for pkg in (tools.generated, tools.custom):
        for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{name}")


# convenience alias used by generator
tool = server.tool
