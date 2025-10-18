"""
Emotional Signals API

Provides real-time emotional/cognitive state metrics from ASTRA's monitoring systems.
Integrates with Prometheus metrics and internal cognitive state tracking.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from astra.models.config import Settings, get_settings


router = APIRouter(prefix="/signals", tags=["signals"])


class EmotionalSignal(BaseModel):
    """Emotional/cognitive signal data point."""
    
    label: str = Field(..., description="Signal label (e.g., 'Calm', 'Focus')")
    value: float = Field(..., ge=0.0, le=1.0, description="Normalized signal value 0.0-1.0")
    threshold: float | None = Field(None, ge=0.0, le=1.0, description="Optional alert threshold")
    unit: str = Field("normalized", description="Signal unit")
    source: str = Field("astra_metrics", description="Signal source system")


class EmotionalSignalsResponse(BaseModel):
    """Response containing emotional signals."""
    
    signals: List[EmotionalSignal]
    timestamp: float = Field(..., description="Unix timestamp of signal capture")
    sacred_code: str = Field("333", description="ASTRA alignment marker")


# Mock signal generator (replace with actual metrics integration)
def _generate_mock_signals() -> List[EmotionalSignal]:
    """
    Generate mock emotional signals.
    
    TODO: Replace with actual Prometheus metrics mapping or cognitive state queries.
    """
    import random
    import time
    
    # Use time-based seed for semi-realistic variation
    seed = int(time.time() / 10) % 1000
    random.seed(seed)
    
    base_signals = {
        "Calm": 0.70,
        "Focus": 0.80,
        "Fatigue": 0.15,
        "Flow": 0.65,
        "Stress": 0.10,
        "Confidence": 0.75
    }
    
    signals = []
    for label, base_value in base_signals.items():
        # Add small random variation
        variation = random.uniform(-0.1, 0.1)
        value = max(0.0, min(1.0, base_value + variation))
        
        # Set thresholds for negative states
        threshold = 0.3 if label in ["Fatigue", "Stress"] else None
        
        signals.append(EmotionalSignal(
            label=label,
            value=value,
            threshold=threshold,
            unit="normalized",
            source="astra_cognitive_monitor"
        ))
    
    return signals


def _get_prometheus_signals(settings: Settings) -> List[EmotionalSignal]:
    """
    Get emotional signals from Prometheus metrics.
    
    Maps Prometheus gauges to emotional/cognitive signals:
    - astra_cognitive_calm_ratio → Calm
    - astra_cognitive_focus_score → Focus
    - astra_system_fatigue_level → Fatigue
    - astra_cognitive_flow_state → Flow
    - astra_system_stress_level → Stress
    - astra_cognitive_confidence → Confidence
    
    Args:
        settings: ASTRA settings with Prometheus configuration
    
    Returns:
        List of emotional signals from metrics
    
    TODO: Implement actual Prometheus client integration
    """
    # For now, return mock signals
    # In production, query Prometheus API and map gauges to signals
    return _generate_mock_signals()


@router.get(
    "/emotion",
    response_model=EmotionalSignalsResponse,
    summary="Get emotional state signals",
    description="Returns current emotional/cognitive state signals for visualization"
)
async def get_emotional_signals(
    settings: Settings = Depends(get_settings)
) -> EmotionalSignalsResponse:
    """
    Get current emotional state signals.
    
    Returns normalized emotional/cognitive signals derived from:
    - Prometheus metrics (system load, response times, error rates)
    - Cognitive state tracking (focus, flow, fatigue)
    - Internal monitoring (stress levels, confidence scores)
    
    Signals are normalized to 0.0-1.0 range for consistent visualization.
    
    Returns:
        EmotionalSignalsResponse with current signal values
    """
    import time
    
    # Get signals from monitoring systems
    signals = _get_prometheus_signals(settings)
    
    return EmotionalSignalsResponse(
        signals=signals,
        timestamp=time.time(),
        sacred_code="333"
    )


@router.get(
    "/cognitive",
    response_model=EmotionalSignalsResponse,
    summary="Get cognitive state signals",
    description="Returns cognitive performance signals (focus, flow, processing)"
)
async def get_cognitive_signals(
    settings: Settings = Depends(get_settings)
) -> EmotionalSignalsResponse:
    """
    Get current cognitive state signals.
    
    Focuses on cognitive performance metrics:
    - Focus: Attention/concentration level
    - Flow: Flow state indicator
    - Processing: Cognitive load level
    - Clarity: Decision clarity score
    
    Returns:
        EmotionalSignalsResponse with cognitive signal values
    """
    import time
    import random
    
    seed = int(time.time() / 10) % 1000
    random.seed(seed)
    
    signals = [
        EmotionalSignal(
            label="Focus",
            value=random.uniform(0.7, 0.9),
            threshold=0.5,
            source="cognitive_monitor"
        ),
        EmotionalSignal(
            label="Flow",
            value=random.uniform(0.6, 0.8),
            threshold=0.4,
            source="cognitive_monitor"
        ),
        EmotionalSignal(
            label="Processing",
            value=random.uniform(0.5, 0.7),
            source="cognitive_monitor"
        ),
        EmotionalSignal(
            label="Clarity",
            value=random.uniform(0.65, 0.85),
            threshold=0.5,
            source="cognitive_monitor"
        )
    ]
    
    return EmotionalSignalsResponse(
        signals=signals,
        timestamp=time.time(),
        sacred_code="333"
    )


@router.get(
    "/system",
    response_model=EmotionalSignalsResponse,
    summary="Get system health signals",
    description="Returns system health/performance signals"
)
async def get_system_signals(
    settings: Settings = Depends(get_settings)
) -> EmotionalSignalsResponse:
    """
    Get current system health signals.
    
    Maps system metrics to signal format:
    - CPU: CPU utilization (inverted, 0=high, 1=low)
    - Memory: Memory availability (0=low, 1=high)
    - Latency: Response time quality (0=slow, 1=fast)
    - Errors: Error rate (inverted, 0=high errors, 1=no errors)
    
    Returns:
        EmotionalSignalsResponse with system signal values
    """
    import time
    import random
    import psutil
    
    # Get real system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
    mem = psutil.virtual_memory()
    mem_percent = mem.percent / 100.0
    
    seed = int(time.time() / 10) % 1000
    random.seed(seed)
    
    signals = [
        EmotionalSignal(
            label="CPU",
            value=1.0 - cpu_percent,  # Invert: low usage = good
            threshold=0.3,  # Alert if usage > 70%
            source="system_monitor"
        ),
        EmotionalSignal(
            label="Memory",
            value=1.0 - mem_percent,  # Invert: low usage = good
            threshold=0.2,  # Alert if usage > 80%
            source="system_monitor"
        ),
        EmotionalSignal(
            label="Latency",
            value=random.uniform(0.75, 0.95),  # Mock latency score
            threshold=0.5,
            source="system_monitor"
        ),
        EmotionalSignal(
            label="Errors",
            value=random.uniform(0.90, 0.99),  # Mock error rate (inverted)
            threshold=0.8,
            source="system_monitor"
        )
    ]
    
    return EmotionalSignalsResponse(
        signals=signals,
        timestamp=time.time(),
        sacred_code="333"
    )
