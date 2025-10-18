"""
ASTRA Safety Policy Tests
Validates safety policy rules and risk calculations.
Created: October 16, 2025
"""
import pytest
from pathlib import Path
from ..core.safety_policy import (
    SafetyPolicy, ConsentLevel, RiskLevel, Capability
)

@pytest.fixture
def policy():
    """Test safety policy"""
    return SafetyPolicy()

def test_consent_levels(policy):
    """Test consent level determination"""
    # Single capability tests
    assert policy.get_consent_level({Capability.UI_CONTROL}) == ConsentLevel.IMPLICIT
    assert policy.get_consent_level({Capability.CODE_EXEC}) == ConsentLevel.EXPLICIT
    assert policy.get_consent_level({Capability.FILE_DELETE}) == ConsentLevel.EXPLICIT_WITH_BACKUP
    
    # Combined capability tests
    assert policy.get_consent_level({
        Capability.UI_CONTROL,
        Capability.FILE_DELETE
    }) == ConsentLevel.EXPLICIT_WITH_BACKUP
    
    assert policy.get_consent_level({
        Capability.UI_CONTROL,
        Capability.CODE_EXEC
    }) == ConsentLevel.EXPLICIT

def test_backup_requirements(policy):
    """Test backup requirement detection"""
    assert not policy.requires_backup({Capability.UI_CONTROL})
    assert not policy.requires_backup({Capability.CODE_EXEC})
    assert policy.requires_backup({Capability.FILE_DELETE})
    assert policy.requires_backup({Capability.SYSTEM_CONFIG})
    
    # Combined tests
    assert policy.requires_backup({
        Capability.UI_CONTROL,
        Capability.FILE_DELETE
    })

def test_denied_combinations(policy):
    """Test capability combination restrictions"""
    # Allowed combinations
    assert policy.is_combination_allowed({Capability.UI_CONTROL})
    assert policy.is_combination_allowed({
        Capability.UI_CONTROL,
        Capability.CODE_EXEC
    })
    
    # Denied combinations
    assert not policy.is_combination_allowed({
        Capability.FILE_DELETE,
        Capability.SYSTEM_CONFIG
    })
    assert not policy.is_combination_allowed({
        Capability.FILE_DELETE,
        Capability.NETWORK_WRITE
    })

def test_risk_scoring(policy):
    """Test risk score calculation"""
    # Low risk operation
    score = policy.calculate_risk_score(
        capabilities={Capability.UI_CONTROL},
        reversible=True,
        scope="file",
        uncertainty=0.1
    )
    assert policy.get_risk_level(score) == RiskLevel.LOW
    
    # Medium risk operation
    score = policy.calculate_risk_score(
        capabilities={Capability.FILE_DELETE},
        reversible=True,
        scope="directory",
        uncertainty=0.3
    )
    assert policy.get_risk_level(score) == RiskLevel.MEDIUM
    
    # High risk operation
    score = policy.calculate_risk_score(
        capabilities={Capability.FILE_DELETE, Capability.SYSTEM_CONFIG},
        reversible=False,
        scope="system",
        uncertainty=0.7
    )
    assert policy.get_risk_level(score) == RiskLevel.HIGH

def test_protected_paths(policy):
    """Test protected path checks"""
    # Windows paths
    windows_system = Path("C:/Windows")
    assert windows_system in policy.protected_paths
    
    program_files = Path("C:/Program Files")
    assert program_files in policy.protected_paths
    
    # POSIX paths
    etc = Path("/etc")
    assert etc in policy.protected_paths
    
    usr = Path("/usr")
    assert usr in policy.protected_paths

def test_domain_allowlist(policy):
    """Test allowed domains"""
    assert "github.com" in policy.allowed_domains
    assert "pypi.org" in policy.allowed_domains
    assert "npmjs.com" in policy.allowed_domains
    assert "evil.com" not in policy.allowed_domains

def test_risk_thresholds(policy):
    """Test risk threshold boundaries"""
    # Test exact threshold values
    for level, threshold in policy.risk_thresholds.items():
        score = threshold
        assert policy.get_risk_level(score) == level
    
    # Test between thresholds
    low_mid = (policy.risk_thresholds[RiskLevel.LOW] + 
               policy.risk_thresholds[RiskLevel.MEDIUM]) / 2
    assert policy.get_risk_level(low_mid) == RiskLevel.MEDIUM
    
    mid_high = (policy.risk_thresholds[RiskLevel.MEDIUM] + 
                policy.risk_thresholds[RiskLevel.HIGH]) / 2
    assert policy.get_risk_level(mid_high) == RiskLevel.HIGH