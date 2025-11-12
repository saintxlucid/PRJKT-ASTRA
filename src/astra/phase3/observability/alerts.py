"""Alert Rules - Anomaly Detection and Alerting

This module defines alert rules for anomaly detection and operational alerting
in the ASTRA system. Supports threshold-based and statistical anomaly detection.

Key Features:
- Alert rule definition and management
- Multiple alert severity levels
- Threshold and anomaly-based detection
- Alert condition evaluation
- History tracking and statistics
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    SILENCED = "SILENCED"


@dataclass
class AlertCondition:
    """Alert condition definition."""
    metric: str
    operator: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    duration_seconds: int = 60

    def evaluate(self, value: float) -> bool:
        """Evaluate condition against a value.
        
        Args:
            value: Metric value to evaluate
            
        Returns:
            True if condition is met
        """
        if self.operator == "gt":
            return value > self.threshold
        elif self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "lt":
            return value < self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """An alert instance."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    condition: AlertCondition
    status: AlertStatus = AlertStatus.ACTIVE
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000)
    triggered_at_ms: float | None = None
    resolved_at_ms: float | None = None
    evaluation_count: int = 0
    last_value: float | None = None

    def trigger(self) -> None:
        """Trigger the alert."""
        self.status = AlertStatus.ACTIVE
        self.triggered_at_ms = time.time() * 1000
        self.resolved_at_ms = None

    def resolve(self) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at_ms = time.time() * 1000

    def silence(self) -> None:
        """Silence the alert."""
        self.status = AlertStatus.SILENCED

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "status": self.status.value,
            "created_at_ms": self.created_at_ms,
            "triggered_at_ms": self.triggered_at_ms,
            "resolved_at_ms": self.resolved_at_ms,
            "evaluation_count": self.evaluation_count,
            "last_value": self.last_value,
        }


@dataclass
class AlertRule:
    """Alert rule definition."""
    rule_id: str
    rule_name: str
    description: str
    condition: AlertCondition
    severity: AlertSeverity
    enabled: bool = True
    alert_instances: dict[str, Alert] = field(default_factory=dict)

    def evaluate(self, value: float) -> Alert | None:
        """Evaluate rule against a metric value.
        
        Args:
            value: Metric value to evaluate
            
        Returns:
            Alert if condition triggered, None otherwise
        """
        if not self.enabled:
            return None

        if not self.condition.evaluate(value):
            return None

        import uuid
        alert_id = str(uuid.uuid4())
        alert = Alert(
            alert_id=alert_id,
            name=self.rule_name,
            severity=self.severity,
            message=f"{self.rule_name}: {self.description}",
            condition=self.condition,
        )
        alert.trigger()
        alert.last_value = value
        self.alert_instances[alert_id] = alert
        return alert

    def to_dict(self) -> dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "condition": {
                "metric": self.condition.metric,
                "operator": self.condition.operator,
                "threshold": self.condition.threshold,
                "duration_seconds": self.condition.duration_seconds,
            },
        }


class AnomalyDetector:
    """Detects anomalies using statistical methods."""

    def __init__(self, window_size: int = 100):
        """Initialize anomaly detector.
        
        Args:
            window_size: Number of historical values to maintain
        """
        self.window_size = window_size
        self.history: dict[str, list[float]] = {}

    def add_value(self, metric: str, value: float) -> None:
        """Add a value to history.
        
        Args:
            metric: Metric name
            value: Metric value
        """
        if metric not in self.history:
            self.history[metric] = []

        self.history[metric].append(value)

        # Maintain window size
        if len(self.history[metric]) > self.window_size:
            self.history[metric] = self.history[metric][-self.window_size:]

    def detect_anomaly(self, metric: str, value: float, std_dev_threshold: float = 3.0) -> bool:
        """Detect if value is anomalous using Z-score.
        
        Args:
            metric: Metric name
            value: Current value
            std_dev_threshold: Z-score threshold
            
        Returns:
            True if value is anomalous
        """
        if metric not in self.history or len(self.history[metric]) < 2:
            return False

        values = self.history[metric]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return False

        z_score = abs((value - mean) / std_dev)
        return z_score > std_dev_threshold

    def get_stats(self, metric: str) -> dict[str, float]:
        """Get statistics for a metric.
        
        Args:
            metric: Metric name
            
        Returns:
            Dictionary with min, max, mean, std_dev
        """
        if metric not in self.history or not self.history[metric]:
            return {}

        values = self.history[metric]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)

        return {
            "min": min(values),
            "max": max(values),
            "mean": mean,
            "std_dev": variance ** 0.5,
            "count": len(values),
        }


class AlertManager:
    """Manages alert rules and instances."""

    def __init__(self):
        """Initialize alert manager."""
        self.rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.history: list[Alert] = []
        self.anomaly_detector = AnomalyDetector()
        self.max_history = 1000

    def create_rule(
        self,
        rule_id: str,
        rule_name: str,
        description: str,
        metric: str,
        operator: str,
        threshold: float,
        severity: AlertSeverity,
    ) -> AlertRule:
        """Create an alert rule.
        
        Args:
            rule_id: Unique rule identifier
            rule_name: Human-readable name
            description: Rule description
            metric: Metric to monitor
            operator: Comparison operator
            threshold: Alert threshold
            severity: Alert severity
            
        Returns:
            Created AlertRule
        """
        condition = AlertCondition(metric=metric, operator=operator, threshold=threshold)
        rule = AlertRule(
            rule_id=rule_id,
            rule_name=rule_name,
            description=description,
            condition=condition,
            severity=severity,
        )
        self.rules[rule_id] = rule
        return rule

    def evaluate_metric(self, metric: str, value: float) -> list[Alert]:
        """Evaluate a metric against all rules.
        
        Args:
            metric: Metric name
            value: Current value
            
        Returns:
            List of triggered alerts
        """
        alerts = []

        for rule in self.rules.values():
            if rule.condition.metric != metric:
                continue

            alert = rule.evaluate(value)
            if alert:
                self.active_alerts[alert.alert_id] = alert
                alerts.append(alert)

        # Add to history
        self.history.extend(alerts)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return alerts

    def detect_anomalies(self, metric: str, value: float) -> list[Alert]:
        """Detect anomalies in a metric.
        
        Args:
            metric: Metric name
            value: Current value
            
        Returns:
            List of anomaly alerts
        """
        self.anomaly_detector.add_value(metric, value)
        alerts = []

        if self.anomaly_detector.detect_anomaly(metric, value):
            import uuid
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                name=f"Anomaly: {metric}",
                severity=AlertSeverity.WARNING,
                message=f"Anomalous value detected for {metric}",
                condition=AlertCondition(metric=metric, operator="eq", threshold=value),
            )
            alert.trigger()
            alert.last_value = value
            self.active_alerts[alert.alert_id] = alert
            alerts.append(alert)
            self.history.append(alert)

        return alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert.
        
        Args:
            alert_id: Alert to resolve
            
        Returns:
            True if resolved, False if not found
        """
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts.pop(alert_id)
        alert.resolve()
        self.history.append(alert)
        return True

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active alerts.
        
        Returns:
            List of active alert dictionaries
        """
        return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_alert_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        recent = self.history[-limit:] if limit > 0 else self.history
        return [alert.to_dict() for alert in recent]

    def get_alert_stats(self) -> dict[str, Any]:
        """Get alert statistics.
        
        Returns:
            Dictionary with alert stats
        """
        by_severity = {}
        for alert in self.history:
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_alerts": len(self.history),
            "active_alerts": len(self.active_alerts),
            "by_severity": by_severity,
            "rules_count": len(self.rules),
            "anomalies_detected": sum(
                1 for alert in self.history
                if "Anomaly" in alert.name
            ),
        }
