"""
Self-healing watchdog for ASTRA Core

Restarts the API if it dies or becomes unresponsive.
"""

import time
import subprocess
import requests
import sys
import os

def restart_api():
    """Restart the ASTRA API process"""
    try:
        # Kill existing uvicorn processes
        if os.name == 'nt':  # Windows
            subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe"], stderr=subprocess.DEVNULL)
        else:  # Unix/Linux/Mac
            subprocess.run(["pkill", "-f", "uvicorn"], stderr=subprocess.DEVNULL)
        
        # Restart the API
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "astra.api.app:app", 
            "--host", "0.0.0.0", 
            "--port", "8080"
        ], cwd="src")
        print("🔄 API restarted")
    except Exception as e:
        print(f"❌ Failed to restart API: {e}")

def check_health():
    """Check if the API is healthy"""
    try:
        response = requests.get("http://127.0.0.1:8080/v1/system/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

if __name__ == "__main__":
    print("🩺 Self-healing watchdog started")
    
    while True:
        if not check_health():
            print("⚠️ API health check failed, restarting...")
            restart_api()
        
        time.sleep(30)