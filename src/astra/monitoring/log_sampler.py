"""
Log sampling system to control log volume while preserving important events.
Uses probability-based sampling with priority levels.
"""
import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()

class LogPriority(Enum):
    """Log priority levels for sampling"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

@dataclass
class SamplingConfig:
    """Configuration for log sampling rates"""
    priority: LogPriority
    sample_rate: float  # 0.0-1.0
    force_sample_after: int  # Force sample after N events

class LogSampler:
    """Probabilistic log sampler with priority levels"""
    
    def __init__(self):
        # Default sampling configuration
        self.config: Dict[LogPriority, SamplingConfig] = {
            LogPriority.DEBUG: SamplingConfig(
                priority=LogPriority.DEBUG,
                sample_rate=0.01,  # Sample 1% of debug logs
                force_sample_after=1000
            ),
            LogPriority.INFO: SamplingConfig(
                priority=LogPriority.INFO,
                sample_rate=0.1,  # Sample 10% of info logs
                force_sample_after=100
            ),
            LogPriority.WARNING: SamplingConfig(
                priority=LogPriority.WARNING,
                sample_rate=0.5,  # Sample 50% of warnings
                force_sample_after=10
            ),
            LogPriority.ERROR: SamplingConfig(
                priority=LogPriority.ERROR,
                sample_rate=1.0,  # Log all errors
                force_sample_after=1
            ),
            LogPriority.CRITICAL: SamplingConfig(
                priority=LogPriority.CRITICAL,
                sample_rate=1.0,  # Log all critical events
                force_sample_after=1
            )
        }
        
        # Counters for forced sampling
        self._counters: Dict[LogPriority, int] = {
            level: 0 for level in LogPriority
        }
        
    def should_sample(
        self,
        level: LogPriority,
        context: Optional[Dict] = None
    ) -> bool:
        """
        Determine if an event should be sampled based on priority and context
        
        Args:
            level: Log priority level
            context: Optional context that might affect sampling decision
            
        Returns:
            bool: Whether to sample this event
        """
        config = self.config[level]
        
        # Always sample high priority events
        if level in [LogPriority.ERROR, LogPriority.CRITICAL]:
            return True
            
        # Check for forced sampling
        self._counters[level] += 1
        if self._counters[level] >= config.force_sample_after:
            self._counters[level] = 0
            return True
            
        # Context-based sampling
        if context:
            # Always sample certain error types
            if context.get("error_type") in [
                "security_violation",
                "data_corruption",
                "system_crash"
            ]:
                return True
                
            # Always sample certain user events
            if context.get("user_type") == "admin":
                return True
                
            # Always sample significant memory events
            if context.get("memory_type") == "critical":
                return True
                
        # Probability-based sampling
        return random.random() < config.sample_rate
        
    def update_config(
        self,
        level: LogPriority,
        sample_rate: float,
        force_sample_after: Optional[int] = None
    ) -> None:
        """Update sampling configuration for a priority level"""
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("Sample rate must be between 0.0 and 1.0")
            
        config = self.config[level]
        config.sample_rate = sample_rate
        if force_sample_after is not None:
            config.force_sample_after = force_sample_after
            
    def get_sampling_stats(self) -> Dict[str, Dict]:
        """Get current sampling statistics"""
        stats = {}
        for level in LogPriority:
            config = self.config[level]
            stats[level.name.lower()] = {
                "sample_rate": config.sample_rate,
                "force_sample_after": config.force_sample_after,
                "current_counter": self._counters[level]
            }
        return stats

# Singleton instance
sampler = LogSampler()

def sample_log(
    level: LogPriority,
    message: str,
    context: Optional[Dict] = None
) -> bool:
    """
    Sample a log message based on priority and context
    
    Args:
        level: Log priority level
        message: Log message
        context: Optional context dict
        
    Returns:
        bool: Whether the message was sampled
    """
    if sampler.should_sample(level, context):
        # Add sampling metadata
        if context is None:
            context = {}
        context["sampled"] = True
        context["priority"] = level.name
        
        # Log the message
        log = logger.bind(**context)
        if level == LogPriority.DEBUG:
            log.debug(message)
        elif level == LogPriority.INFO:
            log.info(message)
        elif level == LogPriority.WARNING:
            log.warning(message)
        elif level == LogPriority.ERROR:
            log.error(message)
        elif level == LogPriority.CRITICAL:
            log.critical(message)
            
        return True
        
    return False