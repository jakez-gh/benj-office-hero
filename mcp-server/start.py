import os
import sys

# ensure our package path is discoverable when running from repo root
here = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(here, "src"))

from office_hero_mcp.main import run  # noqa: E402

os.environ.setdefault("MCP_TRANSPORT", os.getenv("MCP_TRANSPORT", "streamable-http"))

if __name__ == "__main__":
    run()
