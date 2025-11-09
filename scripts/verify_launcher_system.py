"""
Verification script for ASTRA Core Autonomous Launcher System
"""

import os
import sys
import subprocess
import json
import time
import requests

def check_file_exists(filepath):
    """Check if a file exists"""
    return os.path.exists(filepath)

def verify_scripts():
    """Verify all required scripts exist"""
    required_scripts = [
        "scripts/hw_detect.py",
        "scripts/verify_model.py",
        "scripts/selfheal.py",
        "scripts/LAUNCH_ASTRA.ps1",
        "scripts/launch_astra.sh"
    ]
    
    print("🔍 Verifying required scripts...")
    for script in required_scripts:
        if check_file_exists(script):
            print(f"✅ {script}")
        else:
            print(f"❌ {script} - MISSING")
            return False
    return True

def verify_model():
    """Verify GPT-OSS model exists"""
    print("\n🔍 Verifying GPT-OSS model...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/verify_model.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("status") == "ok":
                print(f"✅ Model verified: {data['size_gb']} GB, SHA {data['sha']}")
                return True
            else:
                print("❌ Model verification failed")
                return False
        else:
            print("❌ Model verification script failed")
            return False
    except Exception as e:
        print(f"❌ Error running model verification: {e}")
        return False

def verify_hardware_detection():
    """Verify hardware detection works"""
    print("\n🔍 Testing hardware detection...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/hw_detect.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"✅ Hardware detected: {data['os']}, {data['ram_gb']} GB RAM")
            if data['gpu']:
                print(f"   GPU: {data['gpu_name']} ({data['vram_gb']} GB VRAM)")
            else:
                print("   CPU only")
            return True
        else:
            print("❌ Hardware detection failed")
            return False
    except Exception as e:
        print(f"❌ Error running hardware detection: {e}")
        return False

def verify_launcher_powershell():
    """Verify PowerShell launcher exists and is readable"""
    print("\n🔍 Verifying PowerShell launcher...")
    if check_file_exists("scripts/LAUNCH_ASTRA.ps1"):
        print("✅ PowerShell launcher exists")
        return True
    else:
        print("❌ PowerShell launcher missing")
        return False

def verify_launcher_shell():
    """Verify shell launcher exists and is readable"""
    print("\n🔍 Verifying shell launcher...")
    if check_file_exists("scripts/launch_astra.sh"):
        print("✅ Shell launcher exists")
        return True
    else:
        print("❌ Shell launcher missing")
        return False

def run_verification():
    """Run complete verification of the launcher system"""
    print("=" * 60)
    print("ASTRA Core Autonomous Launcher System Verification")
    print("=" * 60)
    
    # Check all scripts exist
    if not verify_scripts():
        return False
    
    # Verify model
    if not verify_model():
        return False
    
    # Test hardware detection
    if not verify_hardware_detection():
        return False
    
    # Verify launchers
    if not verify_launcher_powershell():
        return False
        
    if not verify_launcher_shell():
        return False
    
    print("\n" + "=" * 60)
    print("✅ All verification checks passed!")
    print("🚀 ASTRA Core Autonomous Launcher System is ready for deployment")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)