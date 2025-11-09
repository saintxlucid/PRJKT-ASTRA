"""
ASTRA Prime Request Metrics
Tracks metrics related to sovereign activation and prime requests.
Created: October 18, 2025
"""
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger()

class PrimeRequestMetrics:
    """Metrics for tracking PRIME REQUEST activations"""
    
    def __init__(self, registry=None):
        """Initialize prime request metrics"""
        self.activations_total = Counter(
            'astra_prime_request_activations_total',
            'Total number of prime request activations',
            ['status', 'mode'],
            registry=registry
        )
        
        self.activation_duration = Histogram(
            'astra_prime_request_duration_seconds',
            'Duration of prime request activation sequence',
            ['mode'],
            registry=registry
        )
        
        self.system_readiness = Gauge(
            'astra_system_readiness',
            'Current readiness state of core systems',
            ['system'],
            registry=registry
        )
        
        self.alignment_score = Gauge(
            'astra_creator_alignment_score',
            'Current alignment score with creator',
            registry=registry
        )
        
        # Initialize system readiness metrics
        core_systems = [
            'neural_engine',
            'memory_core', 
            'guardian_firewall',
            'voice_input',
            'vision_integration',
            'task_engine',
            'interface',
            'alignment_check'
        ]
        
        for system in core_systems:
            self.system_readiness.labels(system=system).set(0)

    def record_activation(self, mode: str, status: str = "success") -> None:
        """Record a prime request activation attempt"""
        self.activations_total.labels(
            status=status,
            mode=mode
        ).inc()
        logger.info("Prime request activation recorded", 
                   mode=mode, 
                   status=status)

    def update_system_readiness(self, system: str, ready: bool) -> None:
        """Update readiness state of a core system"""
        self.system_readiness.labels(
            system=system
        ).set(1 if ready else 0)
        
    def set_alignment_score(self, score: float) -> None:
        """Update creator alignment score"""
        self.alignment_score.set(score)
        logger.info("Creator alignment score updated", score=score)

    def start_activation_timer(self, mode: str) -> Histogram.Timer:
        """Start timing an activation sequence"""
        return self.activation_duration.labels(mode=mode).time()

    def get_system_status(self) -> Dict[str, bool]:
        """Get current status of all systems"""
        return {
            system: bool(self.system_readiness.labels(system=system)._value.get())
            for system in ['neural_engine', 'memory_core', 'guardian_firewall',
                         'voice_input', 'vision_integration', 'task_engine',
                         'interface', 'alignment_check']
        }