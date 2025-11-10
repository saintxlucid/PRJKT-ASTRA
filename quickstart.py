#!/usr/bin/env python3
# ASTRA QUICK START LAUNCHER
# Checks services, then launches TUI

import subprocess
import time
import sys
import socket
import os

def check_port(host, port, timeout=2):
    """Check if a port is open."""
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except:
        return False

def main():
    print("\n" + "="*80)
    print("🟢 ASTRA 3.0 — QUICK START LAUNCHER")
    print("="*80 + "\n")

    # Check required endpoints
    endpoints = {
        "SigilGate": ("localhost", 7701),
        "ASTRA Master": ("localhost", 8000),
        "Memory Service": ("localhost", 7007),
        "Supervisor": ("localhost", 7703),
        "Redis": ("localhost", 6379),
        "PostgreSQL": ("localhost", 5432),
        "Jaeger": ("localhost", 16686),
    }

    print("🔍 Checking backend services...\n")
    status_dict = {}
    for name, (host, port) in endpoints.items():
        is_up = check_port(host, port)
        status_dict[name] = is_up
        icon = "✅" if is_up else "❌"
        print(f"  {icon}  {name:<20} ({host}:{port})")

    print()
    
    critical_up = status_dict.get("SigilGate") and status_dict.get("ASTRA Master")
    
    if not critical_up:
        print("⚠️  CRITICAL: SigilGate and/or ASTRA Master are DOWN")
        print("\n   Start them with:")
        print("   → docker compose -f docker-compose.prod.yml up -d")
        print("   → or use deploy_hardened.ps1 start")
        print("\n   Launching TUI anyway (will attempt connection)...\n")
        time.sleep(3)
    else:
        print("✅ All critical services are UP\n")

    # Launch TUI
    print("🚀 Starting ASTRA TUI...\n")
    try:
        subprocess.run([sys.executable, "astra_tui.py"], check=False)
    except KeyboardInterrupt:
        print("\n👋 Goodbye.")
        sys.exit(0)

if __name__ == "__main__":
    main()
