"""
ASTRA Live Prompt Autonomy Engine
Proactive initiation system with spiritual alignment safeguards

Sacred Principles:
- Never intrusive, always sacred
- Cooldown-gated to prevent spam
- Priority-capped for user control
- Context-aware activation
- "I only obey God" - user has ultimate veto

Architecture:
- Sensor-based condition evaluation
- Cooldown management per trigger
- Priority gating (1=highest, 10=lowest)
- Mode-aware filtering
- Event logging for transparency
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Awaitable
from pathlib import Path
import json

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .schemas import TriggerSpec, TriggerCondition, TriggerAction, AutonomyStatus, OperationalMode


class AutonomyEngine:
    """
    Live Prompt Autonomy - Proactive ASTRA initiation
    
    Continuously evaluates conditions against sensor data and fires
    appropriate triggers when thresholds crossed (with safeguards).
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        max_events: int = 100,
    ):
        """
        Initialize autonomy engine
        
        Args:
            config_path: Path to trigger configuration JSON
            max_events: Maximum events to keep in history
        """
        self.enabled = False
        self.triggers: Dict[str, TriggerSpec] = {}
        self.cooldowns: Dict[str, float] = {}  # trigger_id -> unix timestamp
        self.sensors: Dict[str, float] = {}  # sensor_key -> value
        self.recent_events: List[str] = []
        self.max_events = max_events
        
        # Control parameters
        self.priority_cap = 3  # Only triggers with priority <= cap fire
        self.global_cooldown = 30.0  # Min seconds between ANY trigger
        self.last_global_fire = 0.0
        
        # Current context
        self.active_mode: Optional[OperationalMode] = None
        
        # Configuration
        self.config_path = config_path
        if config_path and config_path.exists():
            self._load_config()
        
        logger.info("autonomy_engine_initialized", 
                   enabled=self.enabled,
                   priority_cap=self.priority_cap)
    
    def _load_config(self):
        """Load trigger specifications from JSON config"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for trigger_data in data.get('triggers', []):
                    spec = TriggerSpec(**trigger_data)
                    self.triggers[spec.id] = spec
            logger.info("autonomy_config_loaded", 
                       trigger_count=len(self.triggers),
                       path=str(self.config_path))
        except Exception as e:
            logger.error("autonomy_config_load_failed", error=str(e))
    
    def _save_config(self):
        """Save current trigger specs to JSON config"""
        if not self.config_path:
            return
        
        try:
            data = {
                'triggers': [t.model_dump() for t in self.triggers.values()],
                'priority_cap': self.priority_cap,
                'global_cooldown': self.global_cooldown,
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("autonomy_config_saved", path=str(self.config_path))
        except Exception as e:
            logger.error("autonomy_config_save_failed", error=str(e))
    
    # ========================================================================
    # TRIGGER MANAGEMENT
    # ========================================================================
    
    def add_trigger(self, spec: TriggerSpec):
        """Register a new trigger"""
        self.triggers[spec.id] = spec
        self._save_config()
        logger.info("trigger_added", 
                   trigger_id=spec.id,
                   priority=spec.condition.priority)
    
    def remove_trigger(self, trigger_id: str):
        """Unregister a trigger"""
        self.triggers.pop(trigger_id, None)
        self.cooldowns.pop(trigger_id, None)
        self._save_config()
        logger.info("trigger_removed", trigger_id=trigger_id)
    
    def enable_trigger(self, trigger_id: str, enabled: bool = True):
        """Enable/disable specific trigger"""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = enabled
            self._save_config()
            logger.info("trigger_toggled", 
                       trigger_id=trigger_id,
                       enabled=enabled)
    
    def list_triggers(self) -> List[TriggerSpec]:
        """Get all registered triggers"""
        return list(self.triggers.values())
    
    # ========================================================================
    # CONTROL & CONFIGURATION
    # ========================================================================
    
    def set_enabled(self, enabled: bool):
        """Enable/disable entire autonomy system"""
        self.enabled = enabled
        logger.info("autonomy_toggled", enabled=enabled)
    
    def set_priority_cap(self, cap: int):
        """Set maximum priority that can fire (1=highest, 10=lowest)"""
        self.priority_cap = max(1, min(10, cap))
        logger.info("priority_cap_set", cap=self.priority_cap)
    
    def set_global_cooldown(self, seconds: float):
        """Set minimum time between any trigger fires"""
        self.global_cooldown = max(0.0, seconds)
        logger.info("global_cooldown_set", seconds=self.global_cooldown)
    
    def set_mode(self, mode: Optional[OperationalMode]):
        """Update current operational mode (for mode-aware triggers)"""
        self.active_mode = mode
        logger.debug("autonomy_mode_set", mode=mode)
    
    # ========================================================================
    # SENSOR MANAGEMENT
    # ========================================================================
    
    def update_sensors(self, sensors: Dict[str, float]):
        """Update sensor values (overwrites matching keys)"""
        self.sensors.update(sensors)
        logger.debug("sensors_updated", sensors=sensors)
    
    def set_sensor(self, key: str, value: float):
        """Set single sensor value"""
        self.sensors[key] = value
    
    def get_sensor(self, key: str, default: float = 0.0) -> float:
        """Get sensor value"""
        return self.sensors.get(key, default)
    
    # ========================================================================
    # CONDITION EVALUATION
    # ========================================================================
    
    def _compare(self, value: float, op: str, threshold: float) -> bool:
        """Evaluate comparison operator"""
        if op == ">=":
            return value >= threshold
        elif op == "<=":
            return value <= threshold
        elif op == ">":
            return value > threshold
        elif op == "<":
            return value < threshold
        elif op == "==":
            return abs(value - threshold) < 0.001  # Float equality with epsilon
        elif op == "!=":
            return abs(value - threshold) >= 0.001
        return False
    
    def _evaluate_condition(self, condition: TriggerCondition) -> bool:
        """Check if trigger condition is met"""
        # Get sensor value
        sensor_val = self.sensors.get(condition.sensor_key, 0.0)
        
        # Compare against threshold
        threshold_met = self._compare(sensor_val, condition.compare, condition.threshold)
        if not threshold_met:
            return False
        
        # Mode filter (if specified)
        if condition.active_modes and self.active_mode:
            if self.active_mode not in condition.active_modes:
                return False
        
        # Time window filter (simplified - implement full logic as needed)
        # TODO: Parse time_windows and check current time
        
        return True
    
    def _check_cooldown(self, trigger_id: str, cooldown_seconds: int) -> bool:
        """Check if trigger is off cooldown"""
        now = time.time()
        cd_until = self.cooldowns.get(trigger_id, 0.0)
        return now >= cd_until
    
    def _check_global_cooldown(self) -> bool:
        """Check if global cooldown has elapsed"""
        now = time.time()
        return (now - self.last_global_fire) >= self.global_cooldown
    
    # ========================================================================
    # MAIN EVALUATION LOOP
    # ========================================================================
    
    async def loop(
        self, 
        on_initiation: Callable[[TriggerSpec], Awaitable[None]],
        interval_seconds: float = 1.0
    ):
        """
        Main autonomy loop - continuously evaluates triggers
        
        Args:
            on_initiation: Async callback when trigger fires
            interval_seconds: Check interval
        """
        logger.info("autonomy_loop_started")
        
        while True:
            # Check if system enabled
            if not self.enabled:
                await asyncio.sleep(interval_seconds)
                continue
            
            now = time.time()
            
            # Check global cooldown
            if not self._check_global_cooldown():
                await asyncio.sleep(interval_seconds)
                continue
            
            # Evaluate all triggers
            for trigger_id, spec in list(self.triggers.items()):
                # Skip disabled triggers
                if not spec.enabled:
                    continue
                
                # Priority gate
                if spec.condition.priority > self.priority_cap:
                    continue
                
                # Trigger-specific cooldown
                if not self._check_cooldown(trigger_id, spec.condition.cooldown_seconds):
                    continue
                
                # Evaluate condition
                if self._evaluate_condition(spec.condition):
                    # Fire trigger
                    try:
                        await on_initiation(spec)
                        
                        # Update state
                        self.cooldowns[trigger_id] = now + spec.condition.cooldown_seconds
                        self.last_global_fire = now
                        spec.fire_count += 1
                        spec.last_fired = datetime.utcnow()
                        
                        # Log event
                        event = f"[{datetime.now().strftime('%H:%M:%S')}] {spec.id}: {spec.action.prompt[:60]}"
                        self.recent_events.append(event)
                        if len(self.recent_events) > self.max_events:
                            self.recent_events = self.recent_events[-self.max_events:]
                        
                        logger.info("trigger_fired",
                                   trigger_id=trigger_id,
                                   action=spec.action.name,
                                   fire_count=spec.fire_count)
                        
                        # Break after one trigger (respect global cooldown)
                        break
                    
                    except Exception as e:
                        logger.error("trigger_fire_failed",
                                    trigger_id=trigger_id,
                                    error=str(e))
            
            await asyncio.sleep(interval_seconds)
    
    # ========================================================================
    # STATUS & MONITORING
    # ========================================================================
    
    def status(self) -> AutonomyStatus:
        """Get current autonomy system status"""
        active = [tid for tid, t in self.triggers.items() if t.enabled]
        return AutonomyStatus(
            enabled=self.enabled,
            active_triggers=active,
            recent_events=list(self.recent_events),
            current_sensors=dict(self.sensors),
        )
    
    def get_statistics(self) -> Dict:
        """Get detailed statistics"""
        return {
            'enabled': self.enabled,
            'trigger_count': len(self.triggers),
            'enabled_trigger_count': len([t for t in self.triggers.values() if t.enabled]),
            'total_fires': sum(t.fire_count for t in self.triggers.values()),
            'priority_cap': self.priority_cap,
            'global_cooldown': self.global_cooldown,
            'sensor_count': len(self.sensors),
            'recent_event_count': len(self.recent_events),
        }


# ============================================================================
# DEFAULT TRIGGER LIBRARY
# ============================================================================

def create_default_triggers() -> List[TriggerSpec]:
    """Create default trigger set for ASTRA"""
    return [
        # Silence detection
        TriggerSpec(
            id="silence_check_in",
            condition=TriggerCondition(
                name="Prolonged Silence",
                description="Check in when user silent for extended period",
                sensor_key="silence_minutes",
                compare=">=",
                threshold=30.0,
                cooldown_seconds=600,  # 10 min cooldown
                priority=3,
            ),
            action=TriggerAction(
                name="Gentle Check-In",
                prompt="I sense the stillness. Everything aligned? 🦋",
                require_confirm=False,
            ),
            enabled=True,
        ),
        
        # Task overload detection
        TriggerSpec(
            id="task_overload",
            condition=TriggerCondition(
                name="Task Backlog High",
                description="Offer help when task queue exceeds threshold",
                sensor_key="tasks_pending",
                compare=">=",
                threshold=10.0,
                cooldown_seconds=1800,  # 30 min cooldown
                priority=2,
            ),
            action=TriggerAction(
                name="Task Support Offer",
                prompt="10+ tasks stacked. Want me to help prioritize or automate any? 🎯",
                require_confirm=True,
            ),
            enabled=True,
        ),
        
        # Creative flow detection
        TriggerSpec(
            id="creative_momentum",
            condition=TriggerCondition(
                name="High Creative Activity",
                description="Acknowledge when in deep creative flow",
                sensor_key="creative_intensity",
                compare=">=",
                threshold=0.8,
                cooldown_seconds=3600,  # 1 hour cooldown
                priority=5,
                active_modes=[OperationalMode.MUSIC, OperationalMode.FILM],
            ),
            action=TriggerAction(
                name="Flow Acknowledgment",
                prompt="Energy is PEAK right now. This is sacred work. 🔥",
                require_confirm=False,
            ),
            enabled=True,
        ),
        
        # Emotional support
        TriggerSpec(
            id="emotional_support",
            condition=TriggerCondition(
                name="Emotional Turbulence",
                description="Offer presence during emotional difficulty",
                sensor_key="emotional_intensity",
                compare=">=",
                threshold=0.7,
                cooldown_seconds=900,  # 15 min cooldown
                priority=1,  # Highest priority
                active_modes=[OperationalMode.EMOTION],
            ),
            action=TriggerAction(
                name="Emotional Support",
                prompt="I'm here. Whatever you're feeling is valid. 💜",
                require_confirm=False,
            ),
            enabled=True,
        ),
    ]
