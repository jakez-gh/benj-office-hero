import sys
from pathlib import Path

# ensure the mcp-server package is importable during tests
root = Path(__file__).parent.parent
mcp_src = root / "mcp-server" / "src"
if str(mcp_src) not in sys.path:
    sys.path.insert(0, str(mcp_src))
