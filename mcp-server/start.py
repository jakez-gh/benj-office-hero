import os
import sys

# ensure our package path is discoverable when running from repo root
here = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(here, "src"))

from office_hero_mcp.main import run  # noqa: E402

# default to streamable-http transport so the process binds a TCP port and
# can be discovered by start_services.py. Override with MCP_TRANSPORT=stdio
# for local interactive runs.
os.environ.setdefault("MCP_TRANSPORT", "streamable-http")

if __name__ == "__main__":
    run()
