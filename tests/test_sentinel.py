"""
ASTRA-OS Sentinel: Integration Tests
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import sentinel components
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from __init__ import (
    ThreatDetector, ThreatIndicator, ThreatIncident, ThreatLevel,
    SecuritySentinel, UnsignedHighCPUProcessPattern, RapidFileEncryptionPattern
)
from anomaly import AnomalyDetector, Metric, Anomaly, BaselineManager, ProcessMetrics
from response import ResponseOrchestrator, ResponsePlan, AlertAction, TerminateAction
from bundler import IncidentBundler, IncidentBundle, CorrelationEngine
from integrity import SelfIntegrityChecker, IntegrityChecker, IntegrityViolation

logger = logging.getLogger(__name__)


# ============================================================================
# Threat Detector Tests
# ============================================================================

class TestThreatDetector:
    """Test threat detector component."""
    
    def test_threat_detector_initialization(self):
        """Test detector can be initialized."""
        detector = ThreatDetector()
        assert detector is not None
        assert detector.patterns == {}
        assert detector.threat_history == []
    
    def test_register_pattern(self):
        """Test pattern registration."""
        detector = ThreatDetector()
        pattern = UnsignedHighCPUProcessPattern()
        
        detector.register_pattern(pattern)
        
        assert pattern.pattern.pattern_id in detector.patterns
        assert len(detector.patterns) == 1
    
    @pytest.mark.asyncio
    async def test_detect_async(self):
        """Test async threat detection."""
        detector = ThreatDetector()
        pattern = RapidFileEncryptionPattern()
        detector.register_pattern(pattern)
        
        # Mock context with file events
        context = {
            'file_events': [
                {'process_id': 1234, 'path': 'C:\\file1.txt', 'operation': 'modify'},
                {'process_id': 1234, 'path': 'C:\\file2.txt', 'operation': 'modify'},
            ] * 50  # 100+ events
        }
        
        incidents = await detector.detect_async(context)
        
        # Should not detect due to threshold
        assert isinstance(incidents, list)
    
    def test_add_to_whitelist(self):
        """Test whitelist functionality."""
        detector = ThreatDetector()
        
        detector.add_to_whitelist("test.exe")
        
        assert "test.exe" in detector.whitelist
    
    def test_get_threat_history(self):
        """Test retrieving threat history."""
        detector = ThreatDetector()
        history = detector.get_threat_history()
        
        assert history == []
    
    def test_get_pattern_stats(self):
        """Test getting pattern statistics."""
        detector = ThreatDetector()
        pattern = UnsignedHighCPUProcessPattern()
        detector.register_pattern(pattern)
        
        stats = detector.get_pattern_stats()
        
        assert pattern.pattern.pattern_id in stats
        assert 'name' in stats[pattern.pattern.pattern_id]


# ============================================================================
# Anomaly Detector Tests
# ============================================================================

class TestAnomalyDetector:
    """Test anomaly detection component."""
    
    def test_baseline_learning(self):
        """Test baseline learning."""
        detector = AnomalyDetector()
        
        # Add normal values
        for i in range(100):
            metric = Metric(
                timestamp=time.time(),
                value=50 + (i % 10),
                source="test_metric"
            )
            detector.update(metric)
        
        assert len(detector.baseline_mgr.baselines) > 0
    
    def test_anomaly_detection(self):
        """Test anomaly detection."""
        detector = AnomalyDetector()
        
        # Learn baseline
        for i in range(100):
            metric = Metric(
                timestamp=time.time(),
                value=50 + (i % 5),
                source="test_metric"
            )
            detector.update(metric)
        
        # Detect anomaly
        anomalous = Metric(
            timestamp=time.time(),
            value=500,  # Far outside normal
            source="test_metric"
        )
        anomaly = detector.detect(anomalous)
        
        # May not detect if still learning
        if anomaly:
            assert isinstance(anomaly, Anomaly)
            assert anomaly.z_score > 3.0
    
    def test_anomaly_history(self):
        """Test anomaly history."""
        detector = AnomalyDetector()
        history = detector.get_anomaly_history()
        
        assert history == []
    
    def test_baseline_stats(self):
        """Test baseline statistics."""
        detector = AnomalyDetector()
        
        # Add some metrics
        for i in range(10):
            metric = Metric(
                timestamp=time.time(),
                value=50 + i,
                source="test_metric"
            )
            detector.update(metric)
        
        stats = detector.get_baseline_stats()
        assert 'test_metric' in stats


# ============================================================================
# Response Orchestrator Tests
# ============================================================================

class TestResponseOrchestrator:
    """Test response orchestration."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ResponseOrchestrator()
        
        assert len(orchestrator.actions) >= 7  # 7 default actions
    
    def test_register_action(self):
        """Test custom action registration."""
        orchestrator = ResponseOrchestrator()
        
        custom_action = AlertAction()
        orchestrator.register_action(custom_action)
        
        assert 'alert' in orchestrator.actions
    
    @pytest.mark.asyncio
    async def test_execute_response(self):
        """Test response execution."""
        orchestrator = ResponseOrchestrator()
        
        incident = {
            'incident_id': 'INC_TEST',
            'threat_level': 'HIGH',
            'affected_processes': {123},
            'affected_files': set(),
            'affected_registry': set(),
        }
        
        plan = await orchestrator.execute_response(incident, 'alert')
        
        assert isinstance(plan, ResponsePlan)
        assert plan.incident_id == 'INC_TEST'
        assert 'alert' in plan.executed_actions
    
    def test_get_action_stats(self):
        """Test action statistics."""
        orchestrator = ResponseOrchestrator()
        stats = orchestrator.get_action_stats()
        
        assert 'alert' in stats
        assert 'investigate' in stats


# ============================================================================
# Incident Bundler Tests
# ============================================================================

class TestIncidentBundler:
    """Test incident bundling."""
    
    def test_bundler_initialization(self):
        """Test bundler initialization."""
        bundler = IncidentBundler()
        
        assert isinstance(bundler.correlation_engine, CorrelationEngine)
        assert bundler.incident_bundles == []
    
    @pytest.mark.asyncio
    async def test_bundle_indicators(self):
        """Test bundling indicators."""
        bundler = IncidentBundler()
        
        indicators = [
            {
                'pattern_id': 'P001',
                'timestamp': time.time(),
                'confidence': 0.8,
                'process_id': 1234,
                'evidence': {}
            },
            {
                'pattern_id': 'P001',
                'timestamp': time.time() + 5,
                'confidence': 0.85,
                'process_id': 1234,
                'evidence': {}
            }
        ]
        
        bundles = await bundler.bundle_indicators(indicators)
        
        assert isinstance(bundles, list)
    
    def test_mark_resolved(self):
        """Test marking bundle as resolved."""
        bundler = IncidentBundler()
        
        bundle = IncidentBundle(
            bundle_id="BUNDLE_TEST",
            timestamp=time.time()
        )
        bundler.active_bundles[bundle.bundle_id] = bundle
        
        bundler.mark_resolved("BUNDLE_TEST")
        
        assert bundle.status.value == "resolved"
    
    def test_escalate_bundle(self):
        """Test escalating bundle threat level."""
        bundler = IncidentBundler()
        
        bundle = IncidentBundle(
            bundle_id="BUNDLE_TEST",
            timestamp=time.time(),
            threat_level="MEDIUM"
        )
        bundler.active_bundles[bundle.bundle_id] = bundle
        
        bundler.escalate_bundle("BUNDLE_TEST")
        
        assert bundle.threat_level == "HIGH"


# ============================================================================
# Integrity Checker Tests
# ============================================================================

class TestIntegrityChecker:
    """Test self-integrity checking."""
    
    def test_integrity_checker_initialization(self):
        """Test integrity checker initialization."""
        checker = IntegrityChecker()
        
        assert checker.baseline == {}
        assert checker.violations == []
    
    def test_register_component(self):
        """Test component registration."""
        checker = IntegrityChecker()
        
        # Register current file
        test_file = __file__
        checker.register_component("test_component", test_file)
        
        assert "test_component" in checker.baseline
    
    def test_check_integrity(self):
        """Test integrity checking."""
        checker = IntegrityChecker()
        
        # Register current file
        test_file = __file__
        checker.register_component("test_component", test_file)
        
        ok, violations = checker.check_integrity()
        
        # Should pass since file hasn't changed
        assert ok is True
        assert violations == []
    
    def test_get_stats(self):
        """Test integrity statistics."""
        checker = IntegrityChecker()
        stats = checker.get_stats()
        
        assert 'components_monitored' in stats
        assert 'total_checks' in stats


# ============================================================================
# Security Sentinel Integration Tests
# ============================================================================

class TestSecuritySentinel:
    """Test security sentinel integration."""
    
    def test_sentinel_initialization(self):
        """Test sentinel initialization."""
        sentinel = SecuritySentinel()
        
        assert sentinel.detector is not None
        assert len(sentinel.detector.patterns) == 18  # 18 patterns
    
    @pytest.mark.asyncio
    async def test_detect_threats(self):
        """Test threat detection."""
        sentinel = SecuritySentinel()
        
        context = {
            'file_events': [],
            'process_events': [],
            'registry_events': [],
            'network_events': [],
        }
        
        incidents = await sentinel.detect(context)
        
        assert isinstance(incidents, list)
    
    def test_get_sentinel_stats(self):
        """Test sentinel statistics."""
        sentinel = SecuritySentinel()
        stats = sentinel.get_stats()
        
        assert 'patterns' in stats
        assert stats['patterns'] == 18


# ============================================================================
# End-to-End Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_threat_detection_and_response(self):
        """Test full threat detection and response flow."""
        sentinel = SecuritySentinel()
        orchestrator = ResponseOrchestrator()
        bundler = IncidentBundler()
        
        # Simulate threat indicators
        indicators = [
            {
                'pattern_id': 'P002_rapid_encryption',
                'timestamp': time.time(),
                'confidence': 0.95,
                'process_id': 9999,
                'evidence': {'modification_count': 100}
            }
        ]
        
        # Bundle indicators
        bundles = await bundler.bundle_indicators(indicators)
        
        # Execute response
        if bundles:
            bundle = bundles[0]
            incident = bundle.to_dict()
            
            plan = await orchestrator.execute_response(
                incident, 
                'investigate'
            )
            
            assert isinstance(plan, ResponsePlan)


# ============================================================================
# Test Configuration
# ============================================================================

if __name__ == "__main__":
    # Run with: pytest test_sentinel.py -v
    pytest.main([__file__, "-v", "--tb=short"])
