"""
Bootstrap runner for Ascension Stack that avoids PowerShell quoting issues.

- Ensures ./src is on sys.path so `astra.*` imports resolve
- Starts uvicorn programmatically
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(host: str = "127.0.0.1", port: int = 8765, reload: bool = False) -> None:
    # Put ./src on sys.path (repo root is two levels up from this file)
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Lazy-import uvicorn after sys.path tweak
    try:
        import uvicorn  # type: ignore
    except Exception as exc:
        print("[runner] Missing dependency: uvicorn. Please install uvicorn[standard].")
        raise

    # Start server
    uvicorn.run(
        "astra.visualization.ascension_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    # Basic arg parsing without external deps
    import argparse

    parser = argparse.ArgumentParser(description="Run Ascension Stack server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8765, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    main(args.host, args.port, args.reload)
