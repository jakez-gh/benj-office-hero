import os

from office_hero_mcp.server import load_tools, server


def run():
    """Entry point for MCP server process. Imports tools and launches server."""
    # load all tool modules so they register with server
    load_tools()

    # options configured from env (currently unused but kept for future)
    _ = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    _ = int(os.getenv("MCP_SERVER_PORT", "8000"))

    server.run(transport=os.getenv("MCP_TRANSPORT", "stdio"), mount_path=None)


if __name__ == "__main__":
    run()
