"""
ASTRA-OS Anomaly Detector: Statistical anomaly detection using baselines and LSTM.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Metric:
    """Single metric measurement."""
    timestamp: float
    value: float
    process_id: Optional[int] = None
    source: str = ""


@dataclass
class Baseline:
    """Statistical baseline for anomaly detection."""
    metric_name: str
    mean: float = 0.0
    std_dev: float = 1.0
    min_val: float = 0.0
    max_val: float = 100.0
    samples: int = 0
    last_updated: float = 0.0
    learning: bool = True
    learning_window: int = 300  # seconds


@dataclass
class Anomaly:
    """Detected anomaly."""
    timestamp: float
    metric_name: str
    value: float
    baseline: float
    z_score: float
    confidence: float
    process_id: Optional[int] = None
    severity: str = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'metric_name': self.metric_name,
            'value': self.value,
            'baseline': self.baseline,
            'z_score': self.z_score,
            'confidence': self.confidence,
            'process_id': self.process_id,
            'severity': self.severity,
        }


# ============================================================================
# Baseline Learning
# ============================================================================

class BaselineManager:
    """Manages statistical baselines for metrics."""
    
    def __init__(self, learning_window: int = 3600):
        """Initialize baseline manager.
        
        Args:
            learning_window: Seconds to learn baseline before anomaly detection
        """
        self.baselines: Dict[str, Baseline] = {}
        self.learning_window = learning_window
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.per_process_baselines: Dict[str, Dict[str, Baseline]] = {}  # process_id -> metric -> Baseline
    
    def update(self, metric: Metric) -> bool:
        """Update baseline with new metric value.
        
        Args:
            metric: Metric to update baseline with
            
        Returns:
            True if baseline is still learning
        """
        name = metric.source or "unknown"
        
        # Global baseline
        if name not in self.baselines:
            self.baselines[name] = Baseline(
                metric_name=name,
                last_updated=time.time()
            )
        
        baseline = self.baselines[name]
        self.metric_history[name].append(metric.value)
        
        # Update statistics
        if baseline.learning:
            self._update_stats(baseline, metric.value)
            
            # Check if learning period is over
            if time.time() - baseline.last_updated > self.learning_window:
                baseline.learning = False
                logger.info(f"Baseline learning complete for {name}: "
                           f"μ={baseline.mean:.2f}, σ={baseline.std_dev:.2f}")
        
        return baseline.learning
    
    def _update_stats(self, baseline: Baseline, value: float):
        """Update baseline statistics."""
        baseline.samples += 1
        
        # Running mean
        old_mean = baseline.mean
        baseline.mean = old_mean + (value - old_mean) / baseline.samples
        
        # Running variance (Welford's online algorithm)
        if baseline.samples == 1:
            baseline.std_dev = 0.0
        else:
            m_a = baseline.mean
            m_b = old_mean
            baseline.std_dev = (
                ((baseline.samples - 2) / (baseline.samples - 1)) * baseline.std_dev ** 2 +
                (baseline.samples / ((baseline.samples - 1) ** 2)) * (value - m_b) ** 2
            ) ** 0.5
        
        baseline.min_val = min(baseline.min_val, value)
        baseline.max_val = max(baseline.max_val, value)
        baseline.last_updated = time.time()
    
    def get_baseline(self, metric_name: str, process_id: Optional[int] = None) -> Optional[Baseline]:
        """Get baseline for metric."""
        if process_id and process_id in self.per_process_baselines:
            return self.per_process_baselines[process_id].get(metric_name)
        
        return self.baselines.get(metric_name)
    
    def is_learning(self) -> bool:
        """Check if any baseline is still learning."""
        return any(b.learning for b in self.baselines.values())


# ============================================================================
# Anomaly Detection
# ============================================================================

class AnomalyDetector:
    """Detect anomalies using statistical methods."""
    
    def __init__(self, z_score_threshold: float = 3.0):
        """Initialize anomaly detector.
        
        Args:
            z_score_threshold: Z-score threshold for anomaly (default: 3.0)
        """
        self.baseline_mgr = BaselineManager()
        self.z_score_threshold = z_score_threshold
        self.anomaly_history: List[Anomaly] = []
        self.anomaly_callbacks: List[Any] = []
    
    def update(self, metric: Metric):
        """Update with new metric value."""
        self.baseline_mgr.update(metric)
    
    def detect(self, metric: Metric) -> Optional[Anomaly]:
        """Detect anomaly for metric.
        
        Args:
            metric: Metric to check
            
        Returns:
            Anomaly if detected, None otherwise
        """
        baseline = self.baseline_mgr.get_baseline(metric.source, metric.process_id)
        
        if not baseline or baseline.learning:
            return None
        
        # Calculate z-score
        if baseline.std_dev == 0:
            return None
        
        z_score = (metric.value - baseline.mean) / baseline.std_dev
        
        # Check if anomalous
        if abs(z_score) > self.z_score_threshold:
            anomaly = Anomaly(
                timestamp=metric.timestamp,
                metric_name=metric.source,
                value=metric.value,
                baseline=baseline.mean,
                z_score=z_score,
                confidence=min(0.95, abs(z_score) / 5.0),
                process_id=metric.process_id,
                severity=self._determine_severity(z_score)
            )
            
            self.anomaly_history.append(anomaly)
            self._trigger_callbacks(anomaly)
            
            return anomaly
        
        return None
    
    def _determine_severity(self, z_score: float) -> str:
        """Determine anomaly severity from z-score."""
        abs_z = abs(z_score)
        if abs_z > 5.0:
            return "high"
        elif abs_z > 4.0:
            return "medium"
        else:
            return "low"
    
    def _trigger_callbacks(self, anomaly: Anomaly):
        """Trigger registered anomaly callbacks."""
        for callback in self.anomaly_callbacks:
            try:
                callback(anomaly)
            except Exception as e:
                logger.error(f"Error in anomaly callback: {e}")
    
    def register_callback(self, callback):
        """Register callback for anomalies."""
        self.anomaly_callbacks.append(callback)
    
    def get_anomaly_history(self, limit: int = 100) -> List[Anomaly]:
        """Get recent anomalies."""
        return self.anomaly_history[-limit:]
    
    def get_baseline_stats(self) -> Dict[str, Any]:
        """Get baseline statistics."""
        stats = {}
        for name, baseline in self.baseline_mgr.baselines.items():
            stats[name] = {
                'mean': baseline.mean,
                'std_dev': baseline.std_dev,
                'min': baseline.min_val,
                'max': baseline.max_val,
                'samples': baseline.samples,
                'learning': baseline.learning,
            }
        return stats


# ============================================================================
# Metric Sources
# ============================================================================

class ProcessMetrics:
    """Collect process-level metrics."""
    
    @staticmethod
    def cpu_percent(process_id: int) -> Optional[Metric]:
        """Get CPU percentage for process."""
        try:
            import psutil
            proc = psutil.Process(process_id)
            return Metric(
                timestamp=time.time(),
                value=proc.cpu_percent(),
                process_id=process_id,
                source="process_cpu_percent"
            )
        except Exception:
            return None
    
    @staticmethod
    def memory_mb(process_id: int) -> Optional[Metric]:
        """Get memory usage in MB for process."""
        try:
            import psutil
            proc = psutil.Process(process_id)
            return Metric(
                timestamp=time.time(),
                value=proc.memory_info().rss / (1024 * 1024),
                process_id=process_id,
                source="process_memory_mb"
            )
        except Exception:
            return None
    
    @staticmethod
    def handle_count(process_id: int) -> Optional[Metric]:
        """Get number of open handles."""
        try:
            import psutil
            proc = psutil.Process(process_id)
            return Metric(
                timestamp=time.time(),
                value=proc.num_handles(),
                process_id=process_id,
                source="process_handles"
            )
        except Exception:
            return None
    
    @staticmethod
    def file_descriptor_count(process_id: int) -> Optional[Metric]:
        """Get number of open file descriptors."""
        try:
            import psutil
            proc = psutil.Process(process_id)
            return Metric(
                timestamp=time.time(),
                value=len(proc.open_files()),
                process_id=process_id,
                source="process_fds"
            )
        except Exception:
            return None
    
    @staticmethod
    def thread_count(process_id: int) -> Optional[Metric]:
        """Get number of threads."""
        try:
            import psutil
            proc = psutil.Process(process_id)
            return Metric(
                timestamp=time.time(),
                value=proc.num_threads(),
                process_id=process_id,
                source="process_threads"
            )
        except Exception:
            return None


class SystemMetrics:
    """Collect system-level metrics."""
    
    @staticmethod
    def system_cpu_percent() -> Metric:
        """Get system CPU percentage."""
        import psutil
        return Metric(
            timestamp=time.time(),
            value=psutil.cpu_percent(interval=0.1),
            source="system_cpu_percent"
        )
    
    @staticmethod
    def system_memory_percent() -> Metric:
        """Get system memory percentage."""
        import psutil
        return Metric(
            timestamp=time.time(),
            value=psutil.virtual_memory().percent,
            source="system_memory_percent"
        )
    
    @staticmethod
    def system_disk_io_bytes() -> Metric:
        """Get system disk I/O bytes."""
        import psutil
        io = psutil.disk_io_counters()
        return Metric(
            timestamp=time.time(),
            value=io.read_bytes + io.write_bytes,
            source="system_disk_io_bytes"
        )
    
    @staticmethod
    def system_network_io_bytes() -> Metric:
        """Get system network I/O bytes."""
        import psutil
        net = psutil.net_io_counters()
        return Metric(
            timestamp=time.time(),
            value=net.bytes_sent + net.bytes_recv,
            source="system_network_io_bytes"
        )
    
    @staticmethod
    def process_count() -> Metric:
        """Get total process count."""
        import psutil
        return Metric(
            timestamp=time.time(),
            value=len(psutil.pids()),
            source="system_process_count"
        )


# ============================================================================
# LSTM-based Anomaly Detection (Advanced)
# ============================================================================

class LSTMAnomalyDetector:
    """LSTM-based anomaly detection for time series."""
    
    def __init__(self, window_size: int = 30, threshold: float = 0.5):
        """Initialize LSTM detector.
        
        Args:
            window_size: Number of past values to use for prediction
            threshold: Reconstruction error threshold
        """
        self.window_size = window_size
        self.threshold = threshold
        self.sequences: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size * 2))
        self.anomalies: List[Anomaly] = []
        self.model_trained: bool = False
        
        # Simplified LSTM alternative: exponential weighted moving average
        self.ewma_values: Dict[str, float] = {}
        self.alpha = 0.1  # Smoothing factor
    
    def update(self, metric: Metric):
        """Update with new metric."""
        self.sequences[metric.source].append(metric.value)
        
        # Update EWMA
        if metric.source not in self.ewma_values:
            self.ewma_values[metric.source] = metric.value
        else:
            self.ewma_values[metric.source] = (
                self.alpha * metric.value +
                (1 - self.alpha) * self.ewma_values[metric.source]
            )
    
    def detect(self, metric: Metric) -> Optional[Anomaly]:
        """Detect anomaly using LSTM/EWMA.
        
        Args:
            metric: Metric to check
            
        Returns:
            Anomaly if detected, None otherwise
        """
        if metric.source not in self.ewma_values:
            return None
        
        # Calculate prediction error
        predicted = self.ewma_values[metric.source]
        error = abs(metric.value - predicted) / (predicted + 1)
        
        if error > self.threshold:
            anomaly = Anomaly(
                timestamp=metric.timestamp,
                metric_name=metric.source,
                value=metric.value,
                baseline=predicted,
                z_score=error,
                confidence=min(0.95, error),
                process_id=metric.process_id,
                severity="high" if error > self.threshold * 1.5 else "medium"
            )
            
            self.anomalies.append(anomaly)
            return anomaly
        
        return None


if __name__ == "__main__":
    # Simple test
    detector = AnomalyDetector()
    
    # Simulate baseline learning
    print("Learning baseline...")
    for i in range(100):
        metric = Metric(
            timestamp=time.time(),
            value=50 + np.random.normal(0, 5),  # Mean 50, std dev 5
            source="test_metric"
        )
        detector.update(metric)
    
    # Simulate normal behavior
    print("Testing normal behavior...")
    for i in range(10):
        metric = Metric(
            timestamp=time.time(),
            value=50 + np.random.normal(0, 5),
            source="test_metric"
        )
        anomaly = detector.detect(metric)
        if anomaly:
            print(f"Detected anomaly: {anomaly}")
    
    # Simulate anomaly
    print("Testing anomaly...")
    for i in range(5):
        metric = Metric(
            timestamp=time.time(),
            value=200,  # Far outside normal range
            source="test_metric"
        )
        anomaly = detector.detect(metric)
        if anomaly:
            print(f"Detected anomaly: z_score={anomaly.z_score:.2f}, "
                  f"confidence={anomaly.confidence:.2f}")
    
    print(f"\nBaseline stats: {detector.get_baseline_stats()}")
    print(f"Anomalies detected: {len(detector.anomaly_history)}")
