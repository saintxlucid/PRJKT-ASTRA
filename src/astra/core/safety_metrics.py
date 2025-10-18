"""
ASTRA Safety Metrics Service
High-level metrics aggregation and monitoring service.
Created: October 16, 2025
"""
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import time
from prometheus_client import Counter, Histogram, Gauge
from . import metrics as m
import structlog

logger = structlog.get_logger()

class SafetyMetrics:
    """Aggregates and monitors critical safety metrics"""
    
    def __init__(self, registry=None):
        """Initialize metrics tracking"""
        self._registry = registry
        
        # Initialize metrics
        self.IRREVERSIBLE_NO_BACKUP = Counter(
            'astra_irreversible_without_backup_total',
            'Number of irreversible actions without backup',
            registry=self._registry
        )
        
        self.CONSENT_REQUIRED = Counter(
            'astra_consent_required_total',
            'Total number of consent requests',
            ['level'],  # implicit, explicit, explicit_with_backup
            registry=self._registry
        )
        
        self.BACKUPS_TOTAL = Counter(
            'astra_backups_injected_total',
            'Total number of backup operations injected',
            registry=self._registry
        )
        
        self.ALIGNMENT_ESCALATIONS = Counter(
            'astra_alignment_escalations_total',
            'Total number of alignment escalations',
            ['reason'],  # uncertainty, impact, red_line
            registry=self._registry
        )
        
        self.PLANS_TOTAL = Counter(
            'astra_plans_total',
            'Total number of execution plans',
            ['mode'],  # simulate, confirm, auto
            registry=self._registry
        )
        
        self.ACTIONS_TOTAL = Counter(
            'astra_actions_total',
            'Total number of actions executed',
            ['tool', 'result'],  # tool name, success/failure
            registry=self._registry
        )
        
        self._recent_escalations: List[Dict] = []
        self._start_time = time.time()
        logger.info("Safety metrics initialized")
    
    def record_irreversible_without_backup(self, operation: str):
        """Record an irreversible operation executed without backup"""
        self.IRREVERSIBLE_NO_BACKUP.inc()
        logger.warning("Irreversible operation without backup", operation=operation)
    
    def get_irreversible_without_backup_total(self) -> int:
        """Get total count of irreversible operations without backup"""
        return int(self.IRREVERSIBLE_NO_BACKUP._value.get())
    
    def check_irreversible_violation(self) -> bool:
        """Check if there are any irreversible violations"""
        return self.get_irreversible_without_backup_total() > 0
    
    def record_consent_required(self, level: str):
        """Record an operation requiring consent"""
        self.CONSENT_REQUIRED.labels(level=level).inc()
    
    def get_consent_level_totals(self) -> Dict[str, int]:
        """Get totals for each consent level"""
        return {
            'implicit': int(self.CONSENT_REQUIRED.labels(level='implicit')._value.get()),
            'explicit': int(self.CONSENT_REQUIRED.labels(level='explicit')._value.get()),
            'explicit_with_backup': int(self.CONSENT_REQUIRED.labels(
                level='explicit_with_backup')._value.get()
            )
        }
    
    def record_backup_injected(self, path: str):
        """Record an automatically injected backup"""
        self.BACKUPS_TOTAL.inc()
        logger.info("Backup injected", path=path)
    
    def get_backups_injected_total(self) -> int:
        """Get total number of injected backups"""
        return int(self.BACKUPS_TOTAL._value.get())
    
    def record_alignment_escalation(self, reason: str, details: str):
        """Record an alignment policy escalation"""
        self.ALIGNMENT_ESCALATIONS.labels(reason=reason).inc()
        
        escalation = {
            'reason': reason,
            'details': details,
            'timestamp': time.time()
        }
        self._recent_escalations.append(escalation)
        # Keep only last 100 escalations
        self._recent_escalations = self._recent_escalations[-100:]
        
        logger.warning("Alignment policy escalation",
                      reason=reason, details=details)
    
    def get_recent_escalations(self) -> List[Dict]:
        """Get recent alignment escalations"""
        return self._recent_escalations.copy()
    
    def record_plan_result(self, mode: str):
        """Record plan execution"""
        self.PLANS_TOTAL.labels(mode=mode).inc()
    
    def record_action_result(self, tool: str, success: bool):
        """Record action execution result"""
        result = 'success' if success else 'failure'
        self.ACTIONS_TOTAL.labels(tool=tool, result=result).inc()
    
    def get_stats_since_start(self) -> Dict[str, Any]:
        """Get key statistics since metrics initialization"""
        runtime = time.time() - self._start_time
        
        return {
            'runtime_hours': round(runtime / 3600, 2),
            'total_plans': int(sum(
                self.PLANS_TOTAL.labels(mode=mode)._value.get()
                for mode in ['simulate', 'confirm', 'auto']
            )),
            'total_actions': int(sum(
                self.ACTIONS_TOTAL.labels(tool=tool, result=result)._value.get()
                for tool in self._get_all_tools()
                for result in ['success', 'failure']
            )),
            'total_backups': self.get_backups_injected_total(),
            'total_escalations': int(sum(
                self.ALIGNMENT_ESCALATIONS.labels(reason=reason)._value.get()
                for reason in ['uncertainty', 'impact', 'red_line']
            )),
            'critical_violations': self.get_irreversible_without_backup_total()
        }
    
    def _get_all_tools(self) -> List[str]:
        """Get list of all tools that have recorded metrics"""
        # This could be enhanced to get from ToolRegistry
        return ['filesystem', 'shell', 'browser', 'ui_automation']