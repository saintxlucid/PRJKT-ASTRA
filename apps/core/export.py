"""
Phase 11: IncidentExporter - Incident and Alert Export System

Exports security incidents, policy violations, and anomalies
in multiple formats (JSON, CSV, JSONL) with batch operations.
"""

import asyncio
import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import os


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"


class IncidentCategory(Enum):
    """Incident categories."""
    THREAT = "threat"
    VIOLATION = "violation"
    ANOMALY = "anomaly"
    ERROR = "error"


class SeverityLevel(Enum):
    """Severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IncidentRecord:
    """A security incident or alert record."""
    incident_id: str           # Unique ID
    timestamp: datetime        # When incident occurred
    severity: SeverityLevel    # Severity level
    category: IncidentCategory # Incident category
    component: str             # Source component
    message: str               # Description
    context: Dict[str, Any] = field(default_factory=dict)  # Full context
    tags: Dict[str, str] = field(default_factory=dict)     # Custom tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'incident_id': self.incident_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'category': self.category.value,
            'component': self.component,
            'message': self.message,
            'context': self.context,
            'tags': self.tags,
        }
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row."""
        return [
            self.incident_id,
            self.timestamp.isoformat(),
            self.severity.value,
            self.category.value,
            self.component,
            self.message,
            json.dumps(self.context),
            json.dumps(self.tags),
        ]


@dataclass
class ExportBatch:
    """A batch of records for export."""
    batch_id: str
    format: ExportFormat
    records: List[IncidentRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    exported_at: Optional[datetime] = None
    file_path: Optional[str] = None
    
    def add_record(self, record: IncidentRecord) -> None:
        """Add record to batch."""
        self.records.append(record)
    
    def export_to_file(self, file_path: str) -> None:
        """Export batch to file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.format == ExportFormat.JSON:
            with open(path, 'w') as f:
                json.dump([r.to_dict() for r in self.records], f, indent=2, default=str)
        
        elif self.format == ExportFormat.CSV:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['incident_id', 'timestamp', 'severity', 'category', 'component', 'message', 'context', 'tags'])
                for record in self.records:
                    writer.writerow(record.to_csv_row())
        
        elif self.format == ExportFormat.JSONL:
            with open(path, 'w') as f:
                for record in self.records:
                    f.write(json.dumps(record.to_dict(), default=str) + '\n')
        
        self.file_path = str(path)
        self.exported_at = datetime.utcnow()
    
    def export_to_string(self) -> str:
        """Export batch to string."""
        if self.format == ExportFormat.JSON:
            return json.dumps([r.to_dict() for r in self.records], indent=2, default=str)
        
        elif self.format == ExportFormat.CSV:
            lines = []
            lines.append(','.join(['incident_id', 'timestamp', 'severity', 'category', 'component', 'message', 'context', 'tags']))
            for record in self.records:
                lines.append(','.join(record.to_csv_row()))
            return '\n'.join(lines)
        
        elif self.format == ExportFormat.JSONL:
            lines = [json.dumps(r.to_dict(), default=str) for r in self.records]
            return '\n'.join(lines)
        
        return ""


class IncidentExporter:
    """Export security incidents and alerts."""
    
    def __init__(self, export_dir: str = "exports"):
        """Initialize exporter.
        
        Args:
            export_dir: Base directory for exports
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self._incidents: List[IncidentRecord] = []
        self._batches: Dict[str, ExportBatch] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            'total_incidents': 0,
            'by_category': {},
            'by_severity': {},
            'by_component': {},
            'total_exports': 0,
        }
    
    async def record_incident(
        self,
        category: IncidentCategory,
        severity: SeverityLevel,
        component: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        incident_id: Optional[str] = None,
    ) -> IncidentRecord:
        """Record an incident."""
        if incident_id is None:
            incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{len(self._incidents):06d}"
        
        record = IncidentRecord(
            incident_id=incident_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            category=category,
            component=component,
            message=message,
            context=context or {},
            tags=tags or {},
        )
        
        async with self._lock:
            self._incidents.append(record)
            self._stats['total_incidents'] += 1
            
            # Update category stats
            cat_key = category.value
            self._stats['by_category'][cat_key] = self._stats['by_category'].get(cat_key, 0) + 1
            
            # Update severity stats
            sev_key = severity.value
            self._stats['by_severity'][sev_key] = self._stats['by_severity'].get(sev_key, 0) + 1
            
            # Update component stats
            self._stats['by_component'][component] = self._stats['by_component'].get(component, 0) + 1
        
        return record
    
    async def record_threat(
        self,
        threat_type: str,
        severity: SeverityLevel,
        context: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        """Record a threat detection."""
        return await self.record_incident(
            category=IncidentCategory.THREAT,
            severity=severity,
            component='security_sentinel',
            message=f"Threat detected: {threat_type}",
            context={**(context or {}), 'threat_type': threat_type},
        )
    
    async def record_violation(
        self,
        violation_type: str,
        component: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        """Record a policy violation."""
        return await self.record_incident(
            category=IncidentCategory.VIOLATION,
            severity=SeverityLevel.HIGH,
            component=component,
            message=f"Policy violation: {violation_type}",
            context={**(context or {}), 'violation_type': violation_type},
        )
    
    async def record_anomaly(
        self,
        anomaly_type: str,
        confidence: float,
        component: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IncidentRecord:
        """Record an anomaly detection."""
        severity = SeverityLevel.MEDIUM
        if confidence > 0.9:
            severity = SeverityLevel.HIGH
        elif confidence > 0.95:
            severity = SeverityLevel.CRITICAL
        
        return await self.record_incident(
            category=IncidentCategory.ANOMALY,
            severity=severity,
            component=component,
            message=f"Anomaly detected: {anomaly_type}",
            context={**(context or {}), 'anomaly_type': anomaly_type, 'confidence': confidence},
        )
    
    async def create_batch(self, format: ExportFormat) -> str:
        """Create a new batch."""
        batch_id = f"BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        batch = ExportBatch(batch_id=batch_id, format=format)
        self._batches[batch_id] = batch
        return batch_id
    
    async def add_to_batch(self, batch_id: str, record: IncidentRecord) -> None:
        """Add record to batch."""
        if batch_id in self._batches:
            self._batches[batch_id].add_record(record)
    
    async def finalize_batch(self, batch_id: str, file_path: Optional[str] = None) -> str:
        """Finalize and export batch."""
        if batch_id not in self._batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch = self._batches[batch_id]
        
        if file_path is None:
            format_ext = batch.format.value
            file_path = str(self.export_dir / f"{batch_id}.{format_ext}")
        
        batch.export_to_file(file_path)
        
        async with self._lock:
            self._stats['total_exports'] += 1
        
        return file_path
    
    async def export_incidents(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: ExportFormat = ExportFormat.JSON,
        file_path: Optional[str] = None,
    ) -> str:
        """Export incidents in time range."""
        async with self._lock:
            incidents = self._incidents[:]
        
        # Filter by time
        if start_time:
            incidents = [i for i in incidents if i.timestamp >= start_time]
        if end_time:
            incidents = [i for i in incidents if i.timestamp <= end_time]
        
        batch = ExportBatch(
            batch_id=f"EXPORT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            format=format,
            records=incidents,
        )
        
        if file_path is None:
            format_ext = format.value
            file_path = str(self.export_dir / f"export-{batch.batch_id}.{format_ext}")
        
        batch.export_to_file(file_path)
        
        async with self._lock:
            self._stats['total_exports'] += 1
        
        return file_path
    
    async def export_recent(
        self,
        limit: int = 1000,
        format: ExportFormat = ExportFormat.JSON,
    ) -> str:
        """Export recent incidents."""
        async with self._lock:
            incidents = self._incidents[-limit:]
        
        batch = ExportBatch(
            batch_id=f"RECENT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            format=format,
            records=incidents,
        )
        
        file_path = str(self.export_dir / f"recent-{batch.batch_id}.{format.value}")
        batch.export_to_file(file_path)
        
        return file_path
    
    async def get_incidents(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[IncidentRecord]:
        """Get incidents in time range."""
        async with self._lock:
            incidents = self._incidents[:]
        
        if start_time:
            incidents = [i for i in incidents if i.timestamp >= start_time]
        if end_time:
            incidents = [i for i in incidents if i.timestamp <= end_time]
        
        return incidents
    
    async def get_by_category(self, category: IncidentCategory) -> List[IncidentRecord]:
        """Get incidents by category."""
        async with self._lock:
            return [i for i in self._incidents if i.category == category]
    
    async def get_by_severity(self, severity: SeverityLevel) -> List[IncidentRecord]:
        """Get incidents by severity."""
        async with self._lock:
            return [i for i in self._incidents if i.severity == severity]
    
    async def get_by_component(self, component: str) -> List[IncidentRecord]:
        """Get incidents by component."""
        async with self._lock:
            return [i for i in self._incidents if i.component == component]
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics."""
        return {
            'total_incidents': self._stats['total_incidents'],
            'by_category': dict(self._stats['by_category']),
            'by_severity': dict(self._stats['by_severity']),
            'by_component': dict(self._stats['by_component']),
            'total_exports': self._stats['total_exports'],
        }
    
    async def rotate_exports(self, keep_days: int = 30) -> int:
        """Rotate old export files.
        
        Args:
            keep_days: Number of days to keep exports
        
        Returns:
            Number of files deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        deleted_count = 0
        
        for file_path in self.export_dir.glob('*'):
            if file_path.is_file():
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mod_time < cutoff:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        
        return deleted_count


# Global exporter instance
_global_exporter: Optional[IncidentExporter] = None


def get_exporter(export_dir: str = "exports") -> IncidentExporter:
    """Get or create global exporter."""
    global _global_exporter
    if _global_exporter is None:
        _global_exporter = IncidentExporter(export_dir)
    return _global_exporter


def set_exporter(exporter: IncidentExporter) -> None:
    """Set global exporter."""
    global _global_exporter
    _global_exporter = exporter
