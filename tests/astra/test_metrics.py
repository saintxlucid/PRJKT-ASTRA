"""
ASTRA Metrics Tests
Validates core metrics tracking.
Created: October 16, 2025
"""
import pytest
from prometheus_client import CollectorRegistry
import time
from astra.core.metrics import MetricsManager

class TestMetrics:
    @pytest.fixture
    def registry(self):
        """Fresh registry for each test"""
        return CollectorRegistry()
        
    @pytest.fixture
    def metrics(self, registry):
        """Test metrics instance"""
        return MetricsManager(registry=registry)
    
    def test_irreversible_without_backup(self, metrics):
        """Test critical irreversible ops counter"""
        # Should start at 0
        assert metrics.safety.get_irreversible_without_backup_total() == 0
        
        # Record violation
        metrics.record_irreversible_no_backup("test_op")
        assert metrics.safety.get_irreversible_without_backup_total() == 1
        
        # This metric should trigger alerts
        assert metrics.safety.check_irreversible_violation()
    
    def test_consent_tracking(self, metrics):
        """Test consent level metrics"""
        metrics.record_consent("implicit")
        metrics.record_consent("explicit")
        metrics.record_consent("explicit_with_backup")
        
        totals = metrics.safety.get_consent_level_totals()
        assert totals["implicit"] == 1
        assert totals["explicit"] == 1
        assert totals["explicit_with_backup"] == 1
    
    def test_backup_injection(self, metrics):
        """Test backup injection tracking"""
        metrics.record_backup("/test/file.txt")
        metrics.record_backup("/test/other.txt")
        
        assert metrics.safety.get_backups_injected_total() == 2
    
    def test_alignment_escalations(self, metrics):
        """Test alignment escalation tracking"""
        metrics.record_escalation("high_risk_operation")
        
        escalations = metrics.safety.get_recent_escalations()
        assert len(escalations) == 1
        assert escalations[0]["reason"] == "high_risk_operation"
    
    async def test_action_tracking(self, metrics):
        """Test action tracking decorator"""
        @metrics.track_action("test_tool")
        async def test_action(succeed: bool = True):
            if not succeed:
                raise Exception("Test failure")
            return "ok"
            
        # Test successful action
        await test_action()
        
        # Test failed action
        with pytest.raises(Exception):
            await test_action(succeed=False)
    
    async def test_latency_tracking(self, metrics):
        """Test latency tracking decorators"""
        @metrics.track_llm()
        async def test_llm():
            time.sleep(0.1)
            return "ok"
            
        @metrics.track_memory("write")
        async def test_memory():
            time.sleep(0.1)
            return "ok"
        
        await test_llm()
        await test_memory()
    
    def test_memory_stats(self, metrics):
        """Test memory usage tracking"""
        metrics.update_memory_usage("semantic", 1024)
        metrics.update_memory_usage("episodic", 2048)
        
        # Stats would be available in Prometheus
        
    def test_cache_stats(self, metrics):
        """Test cache stats tracking"""
        metrics.record_cache("hit")
        metrics.record_cache("miss")
        metrics.record_cache("hit")
        
        # Stats would be available in Prometheus