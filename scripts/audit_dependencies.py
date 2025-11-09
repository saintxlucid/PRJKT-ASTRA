"""
ASTRA Dependency Audit Script
==============================

Checks Python dependencies for security issues and outdated packages.
Runs across all ASTRA services.

Usage:
    python scripts/audit_dependencies.py

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list[str], cwd: str = None) -> tuple[int, str]:
    """
    Run a shell command and return exit code + output.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory (optional)
        
    Returns:
        Tuple of (exit_code, output)
    """
    print(f"$ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout + result.stderr
        print(output)
        return result.returncode, output
    except Exception as e:
        print(f"Error running command: {e}")
        return 1, str(e)


def main():
    """Main audit routine."""
    print("="*60)
    print("🔐 ASTRA Dependency Audit")
    print("="*60)
    print()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Check pip itself
    print("## Checking pip installation")
    run_command([sys.executable, "-m", "pip", "--version"])
    print()
    
    # Run pip check (validates dependencies)
    print("## Validating Dependencies")
    exit_code, _ = run_command([sys.executable, "-m", "pip", "check"])
    if exit_code == 0:
        print("✅ All dependencies are compatible")
    else:
        print("❌ Dependency conflicts detected")
    print()
    
    # List outdated packages
    print("## Outdated Packages")
    run_command([sys.executable, "-m", "pip", "list", "--outdated"])
    print()
    
    # Check security vulnerabilities with pip-audit (if available)
    print("## Security Audit")
    audit_code, _ = run_command([sys.executable, "-m", "pip", "install", "pip-audit", "-q"])
    if audit_code == 0:
        run_command([sys.executable, "-m", "pip_audit"])
    else:
        print("⚠️  pip-audit not available, skipping security scan")
        print("   Install with: pip install pip-audit")
    print()
    
    # Service-specific checks
    print("## Service-Specific Dependency Checks")
    print()
    
    services = [
        ("Master API", project_root),
        ("Memory Service", project_root / "astra-os" / "services" / "memory"),
        ("Sigil Gate", project_root / "astra-os" / "services" / "sigil_gate"),
        ("Supervisor", project_root / "astra-os" / "services" / "supervisor"),
    ]
    
    for service_name, service_path in services:
        requirements_file = service_path / "requirements.txt"
        
        if not requirements_file.exists():
            print(f"### {service_name}")
            print(f"⚠️  No requirements.txt found at {requirements_file}")
            print()
            continue
        
        print(f"### {service_name}")
        print(f"Requirements: {requirements_file}")
        
        # Count dependencies
        with open(requirements_file) as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"Dependencies: {len(deps)}")
        
        # Check for unpinned versions (security risk)
        unpinned = [d for d in deps if "==" not in d and ">=" not in d]
        if unpinned:
            print(f"⚠️  Unpinned dependencies: {len(unpinned)}")
            for dep in unpinned[:5]:  # Show first 5
                print(f"   - {dep}")
        else:
            print("✅ All dependencies pinned")
        
        print()
    
    print("="*60)
    print("Audit Complete")
    print("="*60)
    print()
    print("Recommendations:")
    print("  1. Pin all dependency versions (pkg==1.2.3)")
    print("  2. Run 'pip-audit' regularly for CVE scanning")
    print("  3. Update outdated packages carefully with testing")
    print("  4. Use dependabot/renovate for automated updates")


if __name__ == "__main__":
    main()
