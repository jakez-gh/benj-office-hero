import os

from office_hero_mcp.server import load_tools, server


def run():
    """Entry point for MCP server process. Imports tools and launches server.

    Host and port are configured by ``office_hero_mcp.server`` at import time
    from ``MCP_SERVER_HOST`` / ``MCP_SERVER_PORT`` so that any subsequent call
    to ``server.run`` listens on the configured address. The transport is
    selected from ``MCP_TRANSPORT`` (default ``stdio``).
    """
    # load all tool modules so they register with server
    load_tools()

    server.run(transport=os.getenv("MCP_TRANSPORT", "stdio"), mount_path=None)


if __name__ == "__main__":
    run()
