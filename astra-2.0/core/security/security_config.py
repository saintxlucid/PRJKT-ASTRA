"""
ASTRA 2.0 Security Configuration
Defines core security parameters and paths
"""
from pathlib import Path

# Safe root directory for all file operations
SAFE_ROOT = Path.home() / "ASTRA_SAFE"
SAFE_ROOT.mkdir(parents=True, exist_ok=True)

# Audit database path
DB_PATH = SAFE_ROOT / "audit.sqlite3"

# Allowed shell commands
ALLOWLIST_COMMANDS = {
    "echo",              # Basic output
    "dir", "ls",        # Directory listing
    "type", "cat",      # File contents
    "python", "pip",    # Python environment
    "powershell",       # PowerShell (restricted)
    "cmd",              # Command prompt (restricted)
    "git"               # Version control
}

# File operation limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_TOTAL_STORAGE = 1024 * 1024 * 1024  # 1GB

# Process execution limits
PROCESS_TIMEOUT = 10  # seconds
MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB

# Network restrictions
ALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "github.com",
    "pypi.org"
}
DEFAULT_PORT_RANGE = (8000, 9000)