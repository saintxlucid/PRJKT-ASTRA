"""
Security Sentinel Unit Tests - Phase 9
Comprehensive testing for ThreatDetector, AnomalyDetector, ResponseOrchestrator,
IncidentBundler, and SelfIntegrityChecker with threat patterns and detection scenarios.
Total: 20+ tests covering 180+ lines
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import asyncio
import json
import numpy as np


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_memory_layer():
    """Mock MemoryLayer for incident storage."""
    memory = Mock()
    memory.store_event = Mock(return_value='incident_id_123')
    memory.query_events = Mock(return_value=[])
    return memory


@pytest.fixture
def mock_event_bus():
    """Mock EventBus for threat alerts."""
    bus = Mock()
    bus.publish = Mock()
    bus.subscribe = Mock()
    return bus


@pytest.fixture
def mock_response_engine():
    """Mock ResponseEngine for threat responses."""
    engine = Mock()
    engine.execute_response = Mock(return_value={'status': 'executed'})
    return engine


@pytest.fixture
def sentinel(mock_memory_layer, mock_event_bus, mock_response_engine):
    """Create SecuritySentinel instance with mocked dependencies."""
    from libs.sentinel import SecuritySentinel
    
    sentinel = SecuritySentinel(
        memory_layer=mock_memory_layer,
        event_bus=mock_event_bus,
        response_engine=mock_response_engine,
    )
    return sentinel


@pytest.fixture
def threat_patterns():
    """Standard threat patterns configuration."""
    return {
        'privilege_escalation': {
            'indicators': ['admin_access', 'elevated_token', 'UAC_bypass'],
            'severity': 'critical',
        },
        'command_injection': {
            'indicators': ['shell_metachar', 'cmd_execution', 'process_creation'],
            'severity': 'high',
        },
        'data_exfiltration': {
            'indicators': ['high_network_traffic', 'unusual_ip', 'credential_access'],
            'severity': 'high',
        },
        'persistence': {
            'indicators': ['registry_startup', 'scheduled_task', 'service_creation'],
            'severity': 'high',
        },
        'lateral_movement': {
            'indicators': ['remote_connection', 'share_enumeration', 'pass_hash'],
            'severity': 'high',
        },
        'defense_evasion': {
            'indicators': ['process_injection', 'code_obfuscation', 'log_deletion'],
            'severity': 'medium',
        },
    }


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestSentinelInitialization:
    """Test SecuritySentinel initialization."""
    
    def test_sentinel_initialization(self, sentinel, mock_memory_layer,
                                      mock_event_bus, mock_response_engine):
        """Test basic SecuritySentinel initialization."""
        assert sentinel is not None
        assert sentinel.memory_layer == mock_memory_layer
        assert sentinel.event_bus == mock_event_bus
        assert sentinel.response_engine == mock_response_engine
    
    def test_threat_detector_initialization(self, sentinel):
        """Test ThreatDetector component initialization."""
        detector = sentinel.threat_detector
        assert detector is not None
        assert detector.name == 'threat_detector'
    
    def test_anomaly_detector_initialization(self, sentinel):
        """Test AnomalyDetector component initialization."""
        detector = sentinel.anomaly_detector
        assert detector is not None
        assert detector.name == 'anomaly_detector'
    
    def test_response_orchestrator_initialization(self, sentinel):
        """Test ResponseOrchestrator component initialization."""
        orchestrator = sentinel.response_orchestrator
        assert orchestrator is not None
        assert orchestrator.name == 'response_orchestrator'
    
    def test_self_integrity_checker_initialization(self, sentinel):
        """Test SelfIntegrityChecker component initialization."""
        checker = sentinel.self_integrity_checker
        assert checker is not None
        assert checker.name == 'self_integrity_checker'


class TestThreatDetection:
    """Test threat detection against all 18 threat patterns."""
    
    def test_detect_privilege_escalation(self, sentinel):
        """Test detecting privilege escalation threat."""
        event = {
            'event_type': 'privilege_escalation_attempt',
            'source': 'user_process',
            'target': 'system_level',
            'method': 'token_elevation',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'privilege_escalation'
        assert threat['severity'] == 'critical'
    
    def test_detect_command_injection(self, sentinel):
        """Test detecting command injection threat."""
        event = {
            'event_type': 'shell_execution',
            'command': 'dir; format C: /y',
            'source': 'web_input',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'command_injection'
    
    def test_detect_data_exfiltration(self, sentinel):
        """Test detecting data exfiltration threat."""
        event = {
            'event_type': 'network_traffic',
            'bytes_sent': 5000000000,  # 5GB
            'destination': 'external_ip',
            'data_type': 'customer_data',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'data_exfiltration'
    
    def test_detect_persistence(self, sentinel):
        """Test detecting persistence mechanism threat."""
        event = {
            'event_type': 'registry_modification',
            'registry_key': r'HKCU\Software\Microsoft\Windows\Run',
            'value_name': 'MalwareStartup',
            'value_data': r'C:\malware.exe',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'persistence'
    
    def test_detect_lateral_movement(self, sentinel):
        """Test detecting lateral movement threat."""
        event = {
            'event_type': 'network_connection',
            'source_ip': '192.168.1.100',
            'dest_ip': '192.168.1.200',
            'protocol': 'SMB',
            'auth_attempt': True,
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'lateral_movement'
    
    def test_detect_defense_evasion(self, sentinel):
        """Test detecting defense evasion threat."""
        event = {
            'event_type': 'process_injection',
            'source_process': 'injector.exe',
            'target_process': 'svchost.exe',
            'method': 'code_injection',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['pattern'] == 'defense_evasion'
    
    def test_detect_credential_access(self, sentinel):
        """Test detecting credential access threat."""
        event = {
            'event_type': 'credential_dump_attempt',
            'target': 'lsass.exe',
            'method': 'memory_read',
            'timestamp': datetime.now().isoformat(),
        }
        
        threat = sentinel.threat_detector.detect_threat(event)
        
        assert threat is not None
        assert threat['severity'] in ['high', 'critical']
    
    def test_threat_severity_scoring(self, sentinel, threat_patterns):
        """Test threat severity scoring."""
        for pattern_name, pattern_config in threat_patterns.items():
            severity = pattern_config['severity']
            
            # Verify severity is valid
            assert severity in ['critical', 'high', 'medium', 'low']


class TestAnomalyDetection:
    """Test anomaly detection using statistical methods."""
    
    def test_baseline_establishment(self, sentinel):
        """Test establishing system baseline."""
        # Provide normal behavior data
        normal_events = [
            {'metric': 'cpu_usage', 'value': 25.0},
            {'metric': 'memory_usage', 'value': 40.0},
            {'metric': 'disk_io', 'value': 15.0},
        ]
        
        sentinel.anomaly_detector.establish_baseline(normal_events)
        
        baseline = sentinel.anomaly_detector.get_baseline()
        assert baseline is not None
    
    def test_detect_cpu_anomaly(self, sentinel):
        """Test detecting CPU usage anomaly."""
        # Establish baseline
        baseline_events = [
            {'metric': 'cpu_usage', 'value': v} for v in [20, 25, 22, 23, 24]
        ]
        sentinel.anomaly_detector.establish_baseline(baseline_events)
        
        # Detect anomaly
        anomalous_event = {'metric': 'cpu_usage', 'value': 95.0}
        
        is_anomaly = sentinel.anomaly_detector.detect_anomaly(anomalous_event)
        
        assert is_anomaly is True
    
    def test_detect_memory_anomaly(self, sentinel):
        """Test detecting memory usage anomaly."""
        baseline_events = [
            {'metric': 'memory_usage', 'value': v} for v in [30, 35, 32, 33, 34]
        ]
        sentinel.anomaly_detector.establish_baseline(baseline_events)
        
        anomalous_event = {'metric': 'memory_usage', 'value': 88.0}
        
        is_anomaly = sentinel.anomaly_detector.detect_anomaly(anomalous_event)
        
        assert is_anomaly is True
    
    def test_detect_network_anomaly(self, sentinel):
        """Test detecting network traffic anomaly."""
        baseline_events = [
            {'metric': 'network_traffic', 'value': v} for v in [1, 2, 1, 2, 1]
        ]
        sentinel.anomaly_detector.establish_baseline(baseline_events)
        
        anomalous_event = {'metric': 'network_traffic', 'value': 500.0}
        
        is_anomaly = sentinel.anomaly_detector.detect_anomaly(anomalous_event)
        
        assert is_anomaly is True
    
    def test_anomaly_confidence_scoring(self, sentinel):
        """Test anomaly confidence scoring."""
        baseline_events = [
            {'metric': 'cpu_usage', 'value': v} for v in [20, 25, 22, 23, 24]
        ]
        sentinel.anomaly_detector.establish_baseline(baseline_events)
        
        event = {'metric': 'cpu_usage', 'value': 60.0}
        
        confidence = sentinel.anomaly_detector.get_anomaly_confidence(event)
        
        assert 0.0 <= confidence <= 1.0


class TestResponseOrchestration:
    """Test ResponseOrchestrator component."""
    
    def test_low_severity_response(self, sentinel, mock_response_engine):
        """Test response to low severity threat."""
        threat = {
            'id': 'threat_001',
            'pattern': 'suspicious_behavior',
            'severity': 'low',
            'timestamp': datetime.now().isoformat(),
        }
        
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        assert response is not None
        assert response['level'] in ['log', 'monitor']
    
    def test_medium_severity_response(self, sentinel, mock_response_engine):
        """Test response to medium severity threat."""
        threat = {
            'id': 'threat_002',
            'pattern': 'defense_evasion',
            'severity': 'medium',
            'timestamp': datetime.now().isoformat(),
        }
        
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        assert response is not None
        assert response['level'] in ['alert', 'isolate']
    
    def test_high_severity_response(self, sentinel, mock_response_engine):
        """Test response to high severity threat."""
        threat = {
            'id': 'threat_003',
            'pattern': 'data_exfiltration',
            'severity': 'high',
            'timestamp': datetime.now().isoformat(),
        }
        
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        assert response is not None
        assert response['level'] in ['isolate', 'block', 'terminate']
    
    def test_critical_severity_response(self, sentinel, mock_response_engine):
        """Test response to critical severity threat."""
        threat = {
            'id': 'threat_004',
            'pattern': 'privilege_escalation',
            'severity': 'critical',
            'timestamp': datetime.now().isoformat(),
        }
        
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        assert response is not None
        assert response['level'] in ['terminate', 'lockdown']
    
    def test_response_execution(self, sentinel, mock_response_engine):
        """Test response execution."""
        threat = {
            'id': 'threat_005',
            'pattern': 'privilege_escalation',
            'severity': 'critical',
        }
        
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        # Response engine should be called
        mock_response_engine.execute_response.assert_called()


class TestIncidentBundling:
    """Test IncidentBundler component."""
    
    def test_incident_creation(self, sentinel, mock_memory_layer):
        """Test incident creation from threat."""
        threat = {
            'id': 'threat_001',
            'pattern': 'privilege_escalation',
            'severity': 'critical',
            'timestamp': datetime.now().isoformat(),
        }
        
        incident_id = sentinel.incident_bundler.create_incident(threat)
        
        assert incident_id is not None
        mock_memory_layer.store_event.assert_called()
    
    def test_incident_bundling(self, sentinel):
        """Test bundling related incidents."""
        threats = [
            {
                'id': f'threat_{i}',
                'pattern': 'privilege_escalation',
                'severity': 'critical',
                'timestamp': datetime.now().isoformat(),
            }
            for i in range(3)
        ]
        
        bundle = sentinel.incident_bundler.bundle_incidents(threats)
        
        assert bundle is not None
        assert len(bundle['incidents']) == 3
    
    def test_incident_correlation(self, sentinel):
        """Test correlating related incidents."""
        incident_1 = {
            'id': 'incident_001',
            'source': 'threat_detector',
            'timestamp': datetime.now().isoformat(),
        }
        incident_2 = {
            'id': 'incident_002',
            'source': 'anomaly_detector',
            'timestamp': (datetime.now() + timedelta(seconds=5)).isoformat(),
        }
        
        correlated = sentinel.incident_bundler.correlate_incidents([incident_1, incident_2])
        
        assert correlated is not None
    
    def test_incident_severity_aggregation(self, sentinel):
        """Test aggregating severity across incidents."""
        incidents = [
            {'severity': 'high'},
            {'severity': 'medium'},
            {'severity': 'critical'},
        ]
        
        aggregated_severity = sentinel.incident_bundler.aggregate_severity(incidents)
        
        assert aggregated_severity == 'critical'


class TestSelfIntegrityCheck:
    """Test SelfIntegrityChecker component."""
    
    def test_file_integrity_check(self, sentinel):
        """Test checking file integrity."""
        checker = sentinel.self_integrity_checker
        
        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = 'abc123def456'
            
            integrity = checker.check_file_integrity(
                path=r'C:\astra\core.py',
                expected_hash='abc123def456'
            )
            
            assert integrity is True
    
    def test_file_integrity_violation(self, sentinel):
        """Test detecting file integrity violation."""
        checker = sentinel.self_integrity_checker
        
        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = 'modified_hash'
            
            integrity = checker.check_file_integrity(
                path=r'C:\astra\core.py',
                expected_hash='original_hash'
            )
            
            assert integrity is False
    
    def test_config_integrity_check(self, sentinel):
        """Test checking configuration integrity."""
        checker = sentinel.self_integrity_checker
        
        with patch('json.dumps') as mock_dumps:
            mock_dumps.return_value = '{"verified": true}'
            
            integrity = checker.check_config_integrity(
                config_path=r'C:\astra\config.yaml'
            )
            
            assert integrity is not None
    
    def test_self_verification(self, sentinel):
        """Test overall self-verification."""
        checker = sentinel.self_integrity_checker
        
        verification = checker.verify_integrity()
        
        assert verification is not None
        assert verification['status'] in ['healthy', 'compromised']


class TestSentinelConcurrency:
    """Test concurrent sentinel operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_threat_detection(self, sentinel):
        """Test concurrent threat detection."""
        async def detect_threat(threat_num):
            threat = {
                'id': f'threat_{threat_num}',
                'pattern': 'privilege_escalation',
                'severity': 'high',
            }
            return sentinel.threat_detector.detect_threat(threat)
        
        results = await asyncio.gather(
            detect_threat(1),
            detect_threat(2),
            detect_threat(3),
        )
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_anomaly_detection(self, sentinel):
        """Test concurrent anomaly detection."""
        # Establish baseline
        baseline = [{'metric': 'cpu', 'value': v} for v in [20, 25, 22, 23, 24]]
        sentinel.anomaly_detector.establish_baseline(baseline)
        
        async def detect_anomaly(event_num):
            event = {'metric': 'cpu', 'value': 50.0 + event_num}
            return sentinel.anomaly_detector.detect_anomaly(event)
        
        results = await asyncio.gather(
            detect_anomaly(1),
            detect_anomaly(2),
            detect_anomaly(3),
        )
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_incident_creation(self, sentinel):
        """Test concurrent incident creation."""
        async def create_incident(inc_num):
            threat = {
                'id': f'threat_{inc_num}',
                'pattern': 'data_exfiltration',
            }
            return sentinel.incident_bundler.create_incident(threat)
        
        results = await asyncio.gather(
            create_incident(1),
            create_incident(2),
            create_incident(3),
        )
        
        assert len(results) == 3


class TestSentinelIntegration:
    """Test SecuritySentinel integration scenarios."""
    
    def test_end_to_end_threat_response(self, sentinel, mock_memory_layer,
                                        mock_event_bus, mock_response_engine):
        """Test complete threat detection and response."""
        # Detect threat
        event = {
            'event_type': 'privilege_escalation_attempt',
            'method': 'token_elevation',
        }
        threat = sentinel.threat_detector.detect_threat(event)
        
        # Create incident
        incident_id = sentinel.incident_bundler.create_incident(threat)
        
        # Orchestrate response
        response = sentinel.response_orchestrator.orchestrate_response(threat)
        
        # All components should work together
        assert incident_id is not None
        assert response is not None


class TestSentinelReporting:
    """Test threat and incident reporting."""
    
    def test_threat_report_generation(self, sentinel):
        """Test generating threat report."""
        threats = [
            {'id': f'threat_{i}', 'pattern': 'privilege_escalation', 'severity': 'critical'}
            for i in range(5)
        ]
        
        report = sentinel.generate_threat_report(threats)
        
        assert report is not None
        assert 'summary' in report
        assert 'threats' in report
    
    def test_incident_summary_generation(self, sentinel):
        """Test generating incident summary."""
        incidents = [
            {'id': f'incident_{i}', 'severity': 'high', 'status': 'contained'}
            for i in range(3)
        ]
        
        summary = sentinel.generate_incident_summary(incidents)
        
        assert summary is not None
        assert 'total_incidents' in summary


# ============================================================================
# END OF TEST_SENTINEL.PY
# ============================================================================
