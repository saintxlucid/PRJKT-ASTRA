"""
ASTRA startup script.

Run this script to start the ASTRA API server.
"""

import socket
import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

import uvicorn

from astra.models.config import get_settings


import time
import logging
import platform
import subprocess

logger = logging.getLogger("astra.server")

def _try_release_port_windows(port: int) -> bool:
    """Attempt to release a port on Windows using netstat and taskkill."""
    try:
        # Find process using the port
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode()
        if not output:
            return False

        # Extract PID from last column
        for line in output.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                try:
                    # Attempt graceful termination
                    subprocess.run(f"taskkill /PID {pid}", shell=True, check=True)
                    time.sleep(0.5)  # Give process time to exit
                    return True
                except subprocess.CalledProcessError:
                    pass
    except Exception as e:
        logger.debug(f"Port release attempt failed: {e}")
    return False

def _try_release_port_unix(port: int) -> bool:
    """Attempt to release a port on Unix systems using lsof and kill."""
    try:
        # Find process using the port
        cmd = f"lsof -i :{port} -t"
        output = subprocess.check_output(cmd, shell=True).decode()
        if not output:
            return False

        # Try graceful termination of each process
        for pid in output.splitlines():
            try:
                subprocess.run(f"kill {pid}", shell=True, check=True)
                time.sleep(0.5)  # Give process time to exit
                return True
            except subprocess.CalledProcessError:
                pass
    except Exception as e:
        logger.debug(f"Port release attempt failed: {e}")
    return False

def _find_available_port(host: str, preferred_port: int, attempts: int = 10) -> int:
    """
    Find an available TCP port with exponential backoff retry and OS-specific port release.
    
    Args:
        host: Host address to bind to
        preferred_port: Starting port number
        attempts: Maximum number of retry attempts
        
    Returns:
        Available port number
        
    Raises:
        RuntimeError if no port could be found after attempts
    """
    is_windows = platform.system().lower() == "windows"
    backoff = 0.1  # Initial backoff in seconds

    for attempt in range(attempts):
        candidate = preferred_port + attempt
        
        # Try binding to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
                logger.info(f"Found available port: {candidate}")
                return candidate
            except OSError as e:
                logger.debug(f"Port {candidate} in use, attempt {attempt + 1}/{attempts}")
                
                # Attempt OS-specific port release
                released = False
                if is_windows:
                    released = _try_release_port_windows(candidate)
                else:
                    released = _try_release_port_unix(candidate)
                    
                if released:
                    logger.info(f"Successfully released port {candidate}, retrying...")
                    try:
                        # Try binding again
                        sock.bind((host, candidate))
                        logger.info(f"Successfully bound to released port {candidate}")
                        return candidate
                    except OSError:
                        pass
                
                # Exponential backoff before next attempt
                time.sleep(backoff)
                backoff *= 2  # Double the backoff time

    raise RuntimeError(
        f"Unable to find available port starting at {preferred_port} after {attempts} attempts. "
        "Please check for processes holding ports or try a different port range."
    )


def main():
    """Start the ASTRA API server"""
    settings = get_settings()

    print("=" * 60)
    host = settings.server.host
    preferred_port = settings.server.port
    port = _find_available_port(host, preferred_port)

    if port != preferred_port:
        print(f"[warn] Port {preferred_port} unavailable, switching to {port}")

    settings.server.port = port

    print("ASTRA API Server")
    print("=" * 60)
    print(f"Environment: {settings.environment}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"LLM Provider: {settings.llm.provider}")
    print(f"LLM Base URL: {settings.llm.base_url}")
    print(f"Database: {settings.database.url}")
    print(f"Vector Store: {settings.vector_store.persist_directory}")
    print("=" * 60)
    print()

    # Start uvicorn server
    uvicorn.run(
        "astra.api.app:app",
        host=host,
        port=port,
        reload=settings.server.reload,
        log_level=settings.server.log_level.lower(),
    )


if __name__ == "__main__":
    main()
