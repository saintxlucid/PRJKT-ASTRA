#!/usr/bin/env python3
"""
ASTRA 3.0 Deployment Readiness Validation Script
Comprehensive pre-deployment testing and validation
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

def print_header(text: str):
    """Print section header"""
    print("\n" + "="*80)
    print(text)
    print("="*80)

def print_section(number: int, total: int, title: str):
    """Print section title"""
    print(f"\n[{number}/{total}] {title}")

def check_dependencies() -> Tuple[int, int, int]:
    """Check critical Python dependencies"""
    print_section(1, 10, "Critical Dependencies")
    passed, failed, warnings = 0, 0, 0
    
    critical_deps = [
        'fastapi', 'uvicorn', 'pydantic', 'sqlalchemy', 
        'redis', 'httpx', 'openai', 'pytest', 'structlog'
    ]
    
    for dep in critical_deps:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
            passed += 1
        except ImportError:
            print(f"  ✗ {dep} - MISSING")
            failed += 1
    
    return passed, failed, warnings

def check_python_environment() -> Tuple[int, int, int]:
    """Check Python environment"""
    print_section(2, 10, "Python Environment")
    passed, failed, warnings = 0, 0, 0
    
    print(f"  ✓ Python Version: {sys.version.split()[0]}")
    passed += 1
    
    if 'venv' in sys.prefix.lower() or '.venv' in sys.prefix:
        print(f"  ✓ Virtual Environment: Active")
        passed += 1
    else:
        print(f"  ⚠ Virtual Environment: Not detected")
        warnings += 1
    
    print(f"  ✓ Python Prefix: {sys.prefix}")
    passed += 1
    
    return passed, failed, warnings

def check_core_modules() -> Tuple[int, int, int]:
    """Check core module structure"""
    print_section(3, 10, "Core Module Structure")
    passed, failed, warnings = 0, 0, 0
    
    core_paths = [
        'src/astra',
        'src/astra/api',
        'src/astra/core',
        'src/astra/services',
        'src/astra/hardening',
        'src/astra/memory',
        'src/astra/identity'
    ]
    
    for path in core_paths:
        if Path(path).exists():
            print(f"  ✓ {path}")
            passed += 1
        else:
            print(f"  ⚠ {path} - Not found")
            warnings += 1
    
    return passed, failed, warnings

def check_configuration() -> Tuple[int, int, int]:
    """Check configuration files"""
    print_section(4, 10, "Configuration Files")
    passed, failed, warnings = 0, 0, 0
    
    config_files = [
        ('.env', False),
        ('pyproject.toml', True),
        ('pytest.ini', True),
        ('docker-compose.yml', False),
        ('requirements.txt', True)
    ]
    
    for file, required in config_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
            passed += 1
        else:
            if required:
                print(f"  ✗ {file} - MISSING (Required)")
                failed += 1
            else:
                print(f"  ⚠ {file} - Not found")
                warnings += 1
    
    return passed, failed, warnings

def check_hardening() -> Tuple[int, int, int]:
    """Check production hardening modules"""
    print_section(5, 10, "Production Hardening Modules")
    passed, failed, warnings = 0, 0, 0
    
    hardening_modules = [
        'src/astra/hardening/leader.py',
        'src/astra/hardening/secrets.py',
        'src/astra/hardening/validator.py',
        'src/astra/hardening/circuit_breakers.py',
        'src/astra/hardening/rate_limiter.py',
        'src/astra/hardening/tracing.py',
        'src/astra/hardening/health.py'
    ]
    
    for module in hardening_modules:
        if Path(module).exists():
            print(f"  ✓ {Path(module).name}")
            passed += 1
        else:
            print(f"  ⚠ {Path(module).name} - Not found")
            warnings += 1
    
    return passed, failed, warnings

def check_frontends() -> Tuple[int, int, int]:
    """Check frontend assets"""
    print_section(6, 10, "Frontend Assets")
    passed, failed, warnings = 0, 0, 0
    
    frontends = [
        ('pantheon_ui', 'package.json'),
        ('astra-os', 'index.html'),
        ('comet_browser', 'manifest.json')
    ]
    
    for frontend, marker in frontends:
        frontend_path = Path(frontend)
        if frontend_path.exists():
            marker_path = frontend_path / marker
            if marker_path.exists():
                print(f"  ✓ {frontend} (configured)")
                passed += 1
            else:
                print(f"  ⚠ {frontend} (incomplete)")
                warnings += 1
        else:
            print(f"  ⚠ {frontend} - Not found")
            warnings += 1
    
    return passed, failed, warnings

def check_documentation() -> Tuple[int, int, int]:
    """Check documentation"""
    print_section(7, 10, "Documentation")
    passed, failed, warnings = 0, 0, 0
    
    docs = [
        'README.md',
        'MASTER_DOCUMENTATION_OVERVIEW.md',
        'TECHNICAL_SPECIFICATIONS.md',
        'TESTING_REPORT.md',
        'ARCHITECTURE.md'
    ]
    
    for doc in docs:
        if Path(doc).exists():
            size = Path(doc).stat().st_size
            print(f"  ✓ {doc} ({size:,} bytes)")
            passed += 1
        else:
            print(f"  ⚠ {doc} - Not found")
            warnings += 1
    
    return passed, failed, warnings

def check_tests() -> Tuple[int, int, int]:
    """Check test infrastructure"""
    print_section(8, 10, "Test Infrastructure")
    passed, failed, warnings = 0, 0, 0
    
    test_dirs = ['tests', 'tests/unit', 'tests/integration', 'tests/week1']
    total_tests = 0
    
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            test_files = list(Path(test_dir).glob('test_*.py'))
            test_count = len(test_files)
            total_tests += test_count
            print(f"  ✓ {test_dir} ({test_count} test files)")
            passed += 1
        else:
            print(f"  ⚠ {test_dir} - Not found")
            warnings += 1
    
    print(f"\n  Total Test Files: {total_tests}")
    
    return passed, failed, warnings

def check_docker() -> Tuple[int, int, int]:
    """Check Docker infrastructure"""
    print_section(9, 10, "Docker Infrastructure")
    passed, failed, warnings = 0, 0, 0
    
    docker_files = [
        'Dockerfile',
        'docker-compose.yml',
        '.dockerignore'
    ]
    
    for file in docker_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
            passed += 1
        else:
            print(f"  ⚠ {file} - Not found")
            warnings += 1
    
    return passed, failed, warnings

def check_git() -> Tuple[int, int, int]:
    """Check Git repository status"""
    print_section(10, 10, "Git Repository Status")
    passed, failed, warnings = 0, 0, 0
    
    if Path('.git').exists():
        print(f"  ✓ Git repository initialized")
        passed += 1
        
        try:
            branch = subprocess.check_output(
                ['git', 'branch', '--show-current'],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            print(f"  ✓ Current branch: {branch}")
            passed += 1
            
            # Check for uncommitted changes
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                text=True,
                stderr=subprocess.DEVNULL
            )
            if status.strip():
                print(f"  ⚠ Uncommitted changes detected")
                warnings += 1
            else:
                print(f"  ✓ Working directory clean")
                passed += 1
                
            # Check remote
            try:
                remote = subprocess.check_output(
                    ['git', 'remote', 'get-url', 'origin'],
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                print(f"  ✓ Remote: {remote}")
                passed += 1
            except:
                print(f"  ⚠ No remote repository configured")
                warnings += 1
                
        except Exception as e:
            print(f"  ⚠ Could not determine git status")
            warnings += 1
    else:
        print(f"  ✗ No git repository")
        failed += 1
    
    return passed, failed, warnings

def run_quick_tests() -> Tuple[int, int, int]:
    """Run quick validation tests"""
    print_section(0, 0, "Quick Test Execution")
    passed, failed, warnings = 0, 0, 0
    
    # Run week1 tests (minimal security tests)
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/week1/', '-v', '--tb=short', '--timeout=30'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Count passed tests
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'passed' in line.lower():
                    print(f"  ✓ {line.strip()}")
                    passed += 1
        else:
            print(f"  ⚠ Some tests failed or had errors")
            warnings += 1
            
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Tests timed out")
        warnings += 1
    except Exception as e:
        print(f"  ⚠ Could not run tests: {e}")
        warnings += 1
    
    return passed, failed, warnings

def main():
    """Main validation function"""
    print_header("ASTRA 3.0 DEPLOYMENT READINESS VALIDATION")
    print(f"Date: {subprocess.check_output(['date', '/t'], text=True, shell=True).strip()}")
    print(f"Working Directory: {Path.cwd()}")
    
    # Run all checks
    results = {
        'passed': 0,
        'failed': 0,
        'warnings': 0
    }
    
    checks = [
        check_python_environment,
        check_dependencies,
        check_core_modules,
        check_configuration,
        check_hardening,
        check_frontends,
        check_documentation,
        check_tests,
        check_docker,
        check_git,
    ]
    
    for check in checks:
        p, f, w = check()
        results['passed'] += p
        results['failed'] += f
        results['warnings'] += w
    
    # Run quick tests
    p, f, w = run_quick_tests()
    results['passed'] += p
    results['failed'] += f
    results['warnings'] += w
    
    # Summary
    print_header("VALIDATION SUMMARY")
    total = results['passed'] + results['failed'] + results['warnings']
    print(f"Total Checks: {total}")
    print(f"✓ Passed: {results['passed']}")
    print(f"✗ Failed: {results['failed']}")
    print(f"⚠ Warnings: {results['warnings']}")
    print()
    
    # Calculate score
    score = (results['passed'] / total * 100) if total > 0 else 0
    print(f"Deployment Readiness Score: {score:.1f}%")
    print()
    
    # Deployment status
    if score >= 90:
        status = "✅ READY FOR IMMEDIATE DEPLOYMENT"
        exit_code = 0
    elif score >= 75:
        status = "⚠ READY FOR DEPLOYMENT (Minor issues)"
        exit_code = 0
    elif score >= 60:
        status = "⚠ READY FOR TESTING (Address warnings)"
        exit_code = 1
    else:
        status = "✗ NOT READY (Critical issues found)"
        exit_code = 2
    
    print(f"STATUS: {status}")
    print("="*80)
    
    return exit_code

if __name__ == "__main__":
    exit(main())
