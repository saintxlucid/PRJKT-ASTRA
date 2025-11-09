# services/bridge/bridge_server.py
# Thin wrapper to import the ASTRA bridge FastAPI app for production container
import os
from pathlib import Path

# Ensure src is on sys.path if running from services/bridge/
import sys
root = Path(__file__).resolve().parents[2]  # project root
src_path = root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from astra.bridge.tool_bridge_service import app  # noqa: E402

# Optionally override defaults for container port
os.environ.setdefault("BRIDGE_PORT", "8888")
