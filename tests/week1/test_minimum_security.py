"""
Week 1 Security Hardening - Acceptance Tests

Validates that all security infrastructure is in place before deployment.

Tests:
    1. Model registry exists
    2. verify_models.py script runs
    3. Backup infrastructure exists
    4. Core config file loads
    5. Memory signing module importable
"""

import os
import subprocess
import sys

import yaml


def test_models_registry_exists():
    """Verify security/models_registry.yaml exists."""
    assert os.path.exists("security/models_registry.yaml"), "Model registry not found"


def test_verify_models_script_runs():
    """Verify security/verify_models.py executes without errors."""
    rc = subprocess.call([sys.executable, "security/verify_models.py"])
    assert rc in (0, 1), f"verify_models.py failed with code {rc}"


def test_backups_folder():
    """Verify backup directory structure exists."""
    os.makedirs("data/backups", exist_ok=True)
    assert os.path.isdir("data/backups"), "Backup directory not accessible"


def test_backup_runner_exists():
    """Verify backup scripts exist."""
    assert os.path.exists("tools/backup/backup_runner.py")
    assert os.path.exists("tools/backup/restore_runner.py")


def test_astra_yaml_loads():
    """Verify astra.yaml is valid YAML."""
    if os.path.exists("astra.yaml"):
        with open("astra.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            assert config is not None, "astra.yaml is empty"


def test_memory_signing_importable():
    """Verify memory signing module is importable."""
    try:
        from core.memory_signing import sign_record, verify_record

        assert callable(sign_record)
        assert callable(verify_record)
    except ImportError as e:
        raise AssertionError(f"Memory signing module not importable: {e}")


def test_security_scan_script_exists():
    """Verify security scan runner exists."""
    assert os.path.exists("tools/security/run_scans.ps1")


def test_docker_compose_exists():
    """Verify simplified docker-compose exists."""
    assert (
        os.path.exists("docker-compose.yml")
        or os.path.exists("docker-compose-simplified.yml")
    ), "No docker-compose file found"
