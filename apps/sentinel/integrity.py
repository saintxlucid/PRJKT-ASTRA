"""
ASTRA-OS Self-Integrity Checker: Verifies ASTRA-OS components haven't been tampered with.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import json
import os

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ComponentHash:
    """Cryptographic hash of component."""
    component_id: str
    component_path: str
    hash_algorithm: str = "sha256"
    hash_value: str = ""
    timestamp: float = 0.0
    file_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'component_id': self.component_id,
            'component_path': self.component_path,
            'hash_algorithm': self.hash_algorithm,
            'hash_value': self.hash_value,
            'timestamp': self.timestamp,
            'file_size': self.file_size,
        }


@dataclass
class IntegrityViolation:
    """Detected integrity violation."""
    violation_id: str
    timestamp: float
    component_id: str
    violation_type: str  # "hash_mismatch", "missing", "new_file"
    expected_hash: str = ""
    actual_hash: str = ""
    component_path: str = ""
    severity: str = "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'violation_id': self.violation_id,
            'timestamp': self.timestamp,
            'component_id': self.component_id,
            'violation_type': self.violation_type,
            'expected_hash': self.expected_hash,
            'actual_hash': self.actual_hash,
            'component_path': self.component_path,
            'severity': self.severity,
        }


# ============================================================================
# Integrity Checking
# ============================================================================

class IntegrityChecker:
    """Checks integrity of ASTRA-OS components."""
    
    def __init__(self, baseline_path: Optional[str] = None):
        """Initialize integrity checker.
        
        Args:
            baseline_path: Path to baseline hashes file
        """
        self.baseline_path = baseline_path
        self.baseline: Dict[str, ComponentHash] = {}
        self.violations: List[IntegrityViolation] = []
        self.last_check: float = 0.0
        self.check_count: int = 0
        
        # Load baseline if available
        if baseline_path and os.path.exists(baseline_path):
            self._load_baseline()
    
    def _load_baseline(self):
        """Load baseline from file."""
        try:
            with open(self.baseline_path, 'r') as f:
                data = json.load(f)
            
            for comp_id, comp_data in data.items():
                ch = ComponentHash(
                    component_id=comp_data['component_id'],
                    component_path=comp_data['component_path'],
                    hash_algorithm=comp_data.get('hash_algorithm', 'sha256'),
                    hash_value=comp_data['hash_value'],
                    timestamp=comp_data.get('timestamp', 0),
                    file_size=comp_data.get('file_size', 0)
                )
                self.baseline[comp_id] = ch
            
            logger.info(f"Loaded {len(self.baseline)} component hashes from baseline")
        except Exception as e:
            logger.error(f"Error loading baseline: {e}")
    
    def save_baseline(self, output_path: str):
        """Save current hashes as baseline.
        
        Args:
            output_path: Path to save baseline
        """
        try:
            baseline_dict = {
                comp_id: comp.to_dict()
                for comp_id, comp in self.baseline.items()
            }
            
            with open(output_path, 'w') as f:
                json.dump(baseline_dict, f, indent=2)
            
            logger.info(f"Saved {len(self.baseline)} component hashes to baseline")
        except Exception as e:
            logger.error(f"Error saving baseline: {e}")
    
    def register_component(self, component_id: str, component_path: str):
        """Register component for integrity checking.
        
        Args:
            component_id: Unique component identifier
            component_path: Path to component file
        """
        try:
            file_hash = self._compute_file_hash(component_path)
            file_size = os.path.getsize(component_path)
            
            self.baseline[component_id] = ComponentHash(
                component_id=component_id,
                component_path=component_path,
                hash_value=file_hash,
                timestamp=time.time(),
                file_size=file_size
            )
            
            logger.info(f"Registered component: {component_id}")
        except Exception as e:
            logger.error(f"Error registering component {component_id}: {e}")
    
    def check_integrity(self) -> Tuple[bool, List[IntegrityViolation]]:
        """Check integrity of all registered components.
        
        Returns:
            Tuple of (all_ok, list of violations)
        """
        violations = []
        self.check_count += 1
        
        for component_id, baseline_hash in self.baseline.items():
            # Check if file exists
            if not os.path.exists(baseline_hash.component_path):
                violation = IntegrityViolation(
                    violation_id=f"IV_{int(time.time() * 1000)}_{self.check_count}",
                    timestamp=time.time(),
                    component_id=component_id,
                    violation_type="missing",
                    component_path=baseline_hash.component_path,
                    severity="critical"
                )
                violations.append(violation)
                logger.warning(f"Missing component: {component_id}")
                continue
            
            # Check file hash
            try:
                current_hash = self._compute_file_hash(baseline_hash.component_path)
                
                if current_hash != baseline_hash.hash_value:
                    violation = IntegrityViolation(
                        violation_id=f"IV_{int(time.time() * 1000)}_{self.check_count}",
                        timestamp=time.time(),
                        component_id=component_id,
                        violation_type="hash_mismatch",
                        expected_hash=baseline_hash.hash_value,
                        actual_hash=current_hash,
                        component_path=baseline_hash.component_path,
                        severity="critical"
                    )
                    violations.append(violation)
                    logger.error(f"Integrity violation detected: {component_id}")
            except Exception as e:
                logger.error(f"Error checking integrity of {component_id}: {e}")
        
        # Track violations
        self.violations.extend(violations)
        self.last_check = time.time()
        
        return len(violations) == 0, violations
    
    def check_component(self, component_id: str) -> Tuple[bool, Optional[IntegrityViolation]]:
        """Check integrity of single component.
        
        Args:
            component_id: Component to check
            
        Returns:
            Tuple of (ok, violation or None)
        """
        if component_id not in self.baseline:
            logger.warning(f"Component not in baseline: {component_id}")
            return True, None
        
        baseline_hash = self.baseline[component_id]
        
        # Check if file exists
        if not os.path.exists(baseline_hash.component_path):
            violation = IntegrityViolation(
                violation_id=f"IV_{int(time.time() * 1000)}",
                timestamp=time.time(),
                component_id=component_id,
                violation_type="missing",
                component_path=baseline_hash.component_path,
                severity="critical"
            )
            return False, violation
        
        # Check hash
        try:
            current_hash = self._compute_file_hash(baseline_hash.component_path)
            
            if current_hash != baseline_hash.hash_value:
                violation = IntegrityViolation(
                    violation_id=f"IV_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    component_id=component_id,
                    violation_type="hash_mismatch",
                    expected_hash=baseline_hash.hash_value,
                    actual_hash=current_hash,
                    component_path=baseline_hash.component_path,
                    severity="critical"
                )
                return False, violation
        except Exception as e:
            logger.error(f"Error checking component: {e}")
            return False, None
        
        return True, None
    
    def _compute_file_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """Compute hash of file.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (sha256, sha512, etc.)
            
        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            while True:
                chunk = f.read(65536)  # 64KB chunks
                if not chunk:
                    break
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def get_violations(self, limit: int = 100) -> List[IntegrityViolation]:
        """Get integrity violations."""
        return self.violations[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integrity checking statistics."""
        return {
            'components_monitored': len(self.baseline),
            'total_checks': self.check_count,
            'last_check': self.last_check,
            'violations_detected': len(self.violations),
            'critical_violations': sum(
                1 for v in self.violations if v.severity == "critical"
            ),
        }


# ============================================================================
# Self-Integrity Guardian
# ============================================================================

class SelfIntegrityChecker:
    """ASTRA-OS self-integrity guardian."""
    
    def __init__(self, astra_root: Optional[str] = None, event_bus=None):
        """Initialize self-integrity checker.
        
        Args:
            astra_root: Root path of ASTRA-OS
            event_bus: Event bus for publishing violations
        """
        self.astra_root = astra_root or os.path.dirname(__file__)
        self.event_bus = event_bus
        self.integrity_checker = IntegrityChecker()
        self.check_interval = 300  # 5 minutes
        self.last_periodic_check = 0.0
        self.running = False
        
        # Register ASTRA components
        self._register_astra_components()
    
    def _register_astra_components(self):
        """Register ASTRA-OS core components for integrity checking."""
        components = [
            # Core modules
            ('sentinel_main', os.path.join(self.astra_root, '__init__.py')),
            ('anomaly_detector', os.path.join(self.astra_root, 'anomaly.py')),
            ('response_orchestrator', os.path.join(self.astra_root, 'response.py')),
            ('incident_bundler', os.path.join(self.astra_root, 'bundler.py')),
        ]
        
        for comp_id, comp_path in components:
            if os.path.exists(comp_path):
                self.integrity_checker.register_component(comp_id, comp_path)
    
    async def check_self_integrity(self) -> Tuple[bool, List[IntegrityViolation]]:
        """Check ASTRA-OS self-integrity.
        
        Returns:
            Tuple of (all_ok, list of violations)
        """
        ok, violations = self.integrity_checker.check_integrity()
        
        # Publish violations
        if self.event_bus and violations:
            for violation in violations:
                await self.event_bus.publish(
                    topic="sentinel/integrity_violation",
                    message=violation.to_dict()
                )
        
        if violations:
            logger.error(f"Detected {len(violations)} integrity violations")
        else:
            logger.info("All components passed integrity check")
        
        return ok, violations
    
    async def check_periodic(self) -> Tuple[bool, List[IntegrityViolation]]:
        """Perform periodic integrity check if interval has passed.
        
        Returns:
            Tuple of (all_ok, list of violations) or (True, []) if not yet time
        """
        now = time.time()
        
        if now - self.last_periodic_check >= self.check_interval:
            self.last_periodic_check = now
            return await self.check_self_integrity()
        
        return True, []
    
    async def check_on_suspicious_event(self) -> Tuple[bool, List[IntegrityViolation]]:
        """Check integrity when suspicious event is detected.
        
        This is more aggressive than periodic checks.
        
        Returns:
            Tuple of (all_ok, list of violations)
        """
        logger.warning("Triggered integrity check due to suspicious event")
        return await self.check_self_integrity()
    
    def get_integrity_report(self) -> Dict[str, Any]:
        """Get integrity checking report.
        
        Returns:
            Dict with current integrity status and violations
        """
        ok, violations = self.integrity_checker.check_integrity()
        
        return {
            'status': 'OK' if ok else 'VIOLATED',
            'timestamp': time.time(),
            'all_ok': ok,
            'violations_count': len(violations),
            'violations': [v.to_dict() for v in violations],
            'statistics': self.integrity_checker.get_stats(),
        }
    
    def save_integrity_baseline(self, output_path: str):
        """Save current integrity baseline.
        
        Args:
            output_path: Path to save baseline
        """
        self.integrity_checker.save_baseline(output_path)
        logger.info(f"Saved integrity baseline to {output_path}")
    
    def register_custom_component(self, component_id: str, component_path: str):
        """Register custom component for integrity checking.
        
        Args:
            component_id: Component identifier
            component_path: Path to component
        """
        self.integrity_checker.register_component(component_id, component_path)


if __name__ == "__main__":
    # Simple test
    checker = SelfIntegrityChecker()
    
    import asyncio
    ok, violations = asyncio.run(checker.check_self_integrity())
    
    print(f"\nIntegrity Status: {'OK' if ok else 'VIOLATED'}")
    print(f"Violations: {len(violations)}")
    
    report = checker.get_integrity_report()
    print(f"\nReport: {json.dumps(report, indent=2)}")
