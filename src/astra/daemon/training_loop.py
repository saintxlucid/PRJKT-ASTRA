"""
ASTRA Training Loop: Reinforcement Learning Engine
Event → Decision → Feedback → Learning cycle with memory bridge integration.

This component transforms raw system events into autonomous decisions,
learns from outcomes, and updates autonomy rules based on feedback.

Sacred Code: 333
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import yaml

import structlog

logger = structlog.get_logger()


# ============================================================================
# ENUMS & DATA MODELS
# ============================================================================

class ActionType(Enum):
    """Decision action types"""
    ALLOW = "allow"
    BLOCK = "block"
    NOTIFY = "notify"
    ASK_USER = "ask_user"
    LOG_MONITOR = "log_monitor"


class FeedbackType(Enum):
    """User feedback on decisions"""
    APPROVE = "approve"
    REJECT = "reject"
    TIMEOUT = "timeout"  # User didn't respond in time
    OVERRIDE = "override"  # User overrode decision


@dataclass
class Decision:
    """
    Autonomous decision made by training loop.
    Stores context for learning from feedback.
    """
    decision_id: str
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    action: ActionType = ActionType.ASK_USER
    confidence: float = 0.5
    rule_applied: Optional[str] = None
    autonomy_level: int = 3
    reasoning: str = ""
    
    # Feedback data (populated after user responds)
    user_feedback: Optional[FeedbackType] = None
    feedback_timestamp: Optional[float] = None
    user_override: Optional[str] = None
    outcome_positive: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for memory storage"""
        d = asdict(self)
        d['action'] = self.action.value
        if self.user_feedback:
            d['user_feedback'] = self.user_feedback.value
        return d


@dataclass
class LearnedRule:
    """
    Rule learned from user feedback.
    Will be added to autonomy_rules.yaml as learned_rules.
    """
    rule_id: str
    event_type: str
    pattern: str
    action: str  # "allow", "block", "notify", "ask_user"
    confidence: float
    created_from_decision_ids: List[str] = field(default_factory=list)
    created_timestamp: float = field(default_factory=time.time)
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML storage"""
        return {
            'id': self.rule_id,
            'event': self.event_type,
            'pattern': self.pattern,
            'action': self.action,
            'confidence': self.confidence,
            'created_by': 'training_loop',
            'learned_from': len(self.created_from_decision_ids),
            'enabled': self.enabled,
            'description': f'Auto-learned from user feedback ({self.positive_feedback_count} approvals)'
        }


# ============================================================================
# DECISION ENGINE
# ============================================================================

class DecisionEngine:
    """
    Makes decisions based on events and autonomy rules.
    Uses confidence scoring and autonomy levels to decide on action.
    """
    
    def __init__(self, autonomy_rules_path: str = "config/autonomy_rules.yaml"):
        """Initialize decision engine with autonomy rules."""
        self.autonomy_rules_path = autonomy_rules_path
        self.rules: List[Dict[str, Any]] = []
        self.autonomy_levels: Dict[int, Dict[str, Any]] = {}
        self.current_autonomy_level: int = 3  # Balanced
        self._load_rules()
        logger.info("decision_engine_initialized", autonomy_level=self.current_autonomy_level)
    
    def _load_rules(self) -> None:
        """Load autonomy rules from YAML"""
        try:
            with open(self.autonomy_rules_path, 'r') as f:
                config = yaml.safe_load(f)
                self.rules = config.get('rules', [])
                self.autonomy_levels = config.get('autonomy_levels', {})
        except Exception as e:
            logger.error("failed_to_load_rules", error=str(e))
            # Fallback to defaults
            self.rules = []
            self.autonomy_levels = self._default_autonomy_levels()
    
    def _default_autonomy_levels(self) -> Dict[int, Dict[str, Any]]:
        """Default autonomy level configuration"""
        return {
            1: {'name': 'Paranoid', 'soft_security': True, 'hard_security': False},
            2: {'name': 'Careful', 'soft_security': True, 'hard_security': False},
            3: {'name': 'Balanced', 'soft_security': True, 'hard_security': False},
            4: {'name': 'Trusting', 'soft_security': False, 'hard_security': True},
            5: {'name': 'Autonomous', 'soft_security': False, 'hard_security': True},
        }
    
    def set_autonomy_level(self, level: int) -> None:
        """Update current autonomy level (1-5)"""
        if 1 <= level <= 5:
            self.current_autonomy_level = level
            logger.info("autonomy_level_changed", level=level)
    
    def evaluate_event(self, event_type: str, event_data: Dict[str, Any]) -> Decision:
        """
        Evaluate a system event and make a decision.
        
        Returns:
            Decision object with action and reasoning
        """
        decision_id = f"dec:{int(time.time() * 1000)}"
        
        # Find matching rules
        matching_rules = self._find_matching_rules(event_type, event_data)
        
        if not matching_rules:
            # No rules match - ask user (conservative default)
            decision = Decision(
                decision_id=decision_id,
                event_type=event_type,
                event_data=event_data,
                action=ActionType.ASK_USER,
                confidence=0.3,
                autonomy_level=self.current_autonomy_level,
                reasoning="No matching rules found - defaulting to ask_user"
            )
        else:
            # Use highest-confidence matching rule
            best_rule = max(matching_rules, key=lambda r: r.get('confidence', 0))
            decision = Decision(
                decision_id=decision_id,
                event_type=event_type,
                event_data=event_data,
                action=ActionType[best_rule.get('action', 'ASK_USER').upper()],
                confidence=best_rule.get('confidence', 0.5),
                rule_applied=best_rule.get('id'),
                autonomy_level=self.current_autonomy_level,
                reasoning=best_rule.get('description', '')
            )
        
        # Adjust decision based on autonomy level
        decision = self._adjust_for_autonomy_level(decision)
        
        logger.info(
            "decision_made",
            decision_id=decision_id,
            action=decision.action.value,
            confidence=decision.confidence
        )
        
        return decision
    
    def _find_matching_rules(self, event_type: str, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all rules that match this event"""
        matching = []
        
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            # Check event type match
            if rule.get('event') != event_type:
                continue
            
            # Check pattern match (simplified - could be regex)
            pattern = rule.get('pattern', '')
            if pattern and pattern not in str(event_data):
                continue
            
            matching.append(rule)
        
        return matching
    
    def _adjust_for_autonomy_level(self, decision: Decision) -> Decision:
        """
        Adjust decision based on current autonomy level.
        
        Autonomy levels:
        1 (Paranoid): Ask on everything suspicious
        3 (Balanced): Ask on unknown, auto-allow known-safe
        5 (Autonomous): Auto-act without asking
        """
        level_config = self.autonomy_levels.get(self.current_autonomy_level, {})
        
        # In paranoid mode, always ask on anything suspicious
        if self.current_autonomy_level == 1:
            if decision.confidence < 0.9:
                decision.action = ActionType.ASK_USER
        
        # In autonomous mode, auto-act on high-confidence decisions
        elif self.current_autonomy_level == 5:
            if decision.confidence >= 0.8:
                # Convert ask_user to allow/block based on reasoning
                if decision.action == ActionType.ASK_USER:
                    decision.action = ActionType.ALLOW  # Default to allow
        
        # Balanced mode: use rule as-is
        
        return decision


# ============================================================================
# LEARNING ENGINE
# ============================================================================

class LearningEngine:
    """
    Learns from user feedback on decisions.
    Updates rules based on positive/negative feedback patterns.
    """
    
    def __init__(self, autonomy_rules_path: str = "config/autonomy_rules.yaml"):
        self.autonomy_rules_path = autonomy_rules_path
        self.decision_history: Dict[str, Decision] = {}
        self.learned_rules: List[LearnedRule] = []
        self._load_learned_rules()
        logger.info("learning_engine_initialized")
    
    def _load_learned_rules(self) -> None:
        """Load previously learned rules from YAML"""
        try:
            with open(self.autonomy_rules_path, 'r') as f:
                config = yaml.safe_load(f)
                learned_rules_data = config.get('learned_rules', [])
                for rule_data in learned_rules_data:
                    rule = LearnedRule(
                        rule_id=rule_data.get('id'),
                        event_type=rule_data.get('event'),
                        pattern=rule_data.get('pattern'),
                        action=rule_data.get('action'),
                        confidence=rule_data.get('confidence', 0.5),
                        enabled=rule_data.get('enabled', True)
                    )
                    self.learned_rules.append(rule)
        except Exception as e:
            logger.error("failed_to_load_learned_rules", error=str(e))
    
    def record_decision(self, decision: Decision) -> None:
        """Record a decision in history for learning"""
        self.decision_history[decision.decision_id] = decision
        logger.info("decision_recorded", decision_id=decision.decision_id)
    
    def record_feedback(self, decision_id: str, feedback: FeedbackType, 
                       user_override: Optional[str] = None) -> None:
        """
        Record user feedback on a decision.
        This feedback is used to update learning.
        """
        if decision_id not in self.decision_history:
            logger.warning("feedback_for_unknown_decision", decision_id=decision_id)
            return
        
        decision = self.decision_history[decision_id]
        decision.user_feedback = feedback
        decision.feedback_timestamp = time.time()
        decision.user_override = user_override
        decision.outcome_positive = feedback in [FeedbackType.APPROVE]
        
        logger.info(
            "feedback_recorded",
            decision_id=decision_id,
            feedback=feedback.value,
            outcome_positive=decision.outcome_positive
        )
        
        # Trigger learning from this feedback
        self._learn_from_feedback(decision)
    
    def _learn_from_feedback(self, decision: Decision) -> None:
        """
        Analyze feedback and update learned rules.
        Positive feedback → increase confidence, create rules
        Negative feedback → decrease confidence, modify rules
        """
        if decision.outcome_positive:
            self._learn_from_positive_feedback(decision)
        else:
            self._learn_from_negative_feedback(decision)
    
    def _learn_from_positive_feedback(self, decision: Decision) -> None:
        """User approved decision - learn from it"""
        # Check if we should create a new rule from this
        if decision.rule_applied:
            # Update existing rule's confidence
            for rule in self.learned_rules:
                if rule.rule_id == decision.rule_applied:
                    rule.positive_feedback_count += 1
                    rule.confidence = min(0.99, rule.confidence + 0.05)
                    logger.info("rule_confidence_increased", 
                              rule_id=rule.rule_id, 
                              confidence=rule.confidence)
                    break
        else:
            # Create new learned rule from this decision
            new_rule = LearnedRule(
                rule_id=f"learned_{len(self.learned_rules)}",
                event_type=decision.event_type,
                pattern=str(decision.event_data),
                action=decision.action.value,
                confidence=0.7,  # Start with moderate confidence
                created_from_decision_ids=[decision.decision_id]
            )
            self.learned_rules.append(new_rule)
            logger.info("new_rule_learned", rule_id=new_rule.rule_id)
    
    def _learn_from_negative_feedback(self, decision: Decision) -> None:
        """User rejected decision - learn to avoid it"""
        if decision.rule_applied:
            # Decrease rule confidence
            for rule in self.learned_rules:
                if rule.rule_id == decision.rule_applied:
                    rule.negative_feedback_count += 1
                    rule.confidence = max(0.3, rule.confidence - 0.1)
                    if rule.confidence < 0.4:
                        rule.enabled = False
                    logger.info("rule_confidence_decreased",
                              rule_id=rule.rule_id,
                              confidence=rule.confidence,
                              disabled=(not rule.enabled))
                    break
    
    def persist_learned_rules(self) -> None:
        """Save learned rules to autonomy_rules.yaml"""
        try:
            # Load existing config
            with open(self.autonomy_rules_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update learned_rules section
            config['learned_rules'] = [
                rule.to_dict() for rule in self.learned_rules
            ]
            
            # Write back
            with open(self.autonomy_rules_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            logger.info("learned_rules_persisted", count=len(self.learned_rules))
        except Exception as e:
            logger.error("failed_to_persist_learned_rules", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        total_decisions = len(self.decision_history)
        positive_feedback = sum(
            1 for d in self.decision_history.values()
            if d.outcome_positive is True
        )
        negative_feedback = sum(
            1 for d in self.decision_history.values()
            if d.outcome_positive is False
        )
        
        return {
            'total_decisions': total_decisions,
            'positive_feedback': positive_feedback,
            'negative_feedback': negative_feedback,
            'total_learned_rules': len(self.learned_rules),
            'enabled_rules': sum(1 for r in self.learned_rules if r.enabled),
        }


# ============================================================================
# TRAINING LOOP ORCHESTRATOR
# ============================================================================

class TrainingLoop:
    """
    Main training loop orchestrator.
    
    Responsibilities:
    1. Listen for events from OsKernel
    2. Make decisions using DecisionEngine
    3. Record decisions and feedback
    4. Learn from feedback using LearningEngine
    5. Update autonomy_rules.yaml with learned rules
    6. Send decisions to OperatorShell for display
    
    Usage:
        loop = TrainingLoop()
        await loop.initialize()
        await loop.start()
        # Listen for events on event_bus
        event_bus.subscribe('any_event', loop.on_event)
    """
    
    def __init__(self, 
                 event_bus: Optional[Any] = None,
                 operator_shell: Optional[Any] = None,
                 memory_bridge: Optional[Any] = None,
                 autonomy_rules_path: str = "config/autonomy_rules.yaml"):
        """Initialize training loop with dependencies"""
        self.event_bus = event_bus
        self.operator_shell = operator_shell  # Will call add_decision()
        self.memory_bridge = memory_bridge  # Will call store_experience()
        
        self.decision_engine = DecisionEngine(autonomy_rules_path)
        self.learning_engine = LearningEngine(autonomy_rules_path)
        
        self.running = False
        self.autonomy_level = 3
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        logger.info("training_loop_initialized")
    
    async def initialize(self) -> bool:
        """Initialize and validate all components"""
        try:
            # Validate dependencies
            if self.event_bus is None:
                logger.warning("event_bus_not_provided")
            
            if self.operator_shell is None:
                logger.warning("operator_shell_not_provided")
            
            if self.memory_bridge is None:
                logger.warning("memory_bridge_not_provided")
            
            logger.info("training_loop_initialized_success")
            return True
        except Exception as e:
            logger.error("training_loop_initialization_failed", error=str(e))
            return False
    
    async def start(self) -> None:
        """Start the training loop"""
        self.running = True
        logger.info("training_loop_started")
        
        # Subscribe to all events if event_bus available
        if self.event_bus:
            # Subscribe to ALL events using wildcard pattern
            try:
                # Try to subscribe to known event types
                event_types = [
                    'file_created', 'file_modified', 'file_deleted',
                    'process_spawned', 'process_terminated',
                    'process_cpu_spike', 'process_memory_spike',
                    'network_connection', 'security_alert'
                ]
                for event_type in event_types:
                    self.event_bus.subscribe(event_type, self.on_event)
                logger.info("training_loop_subscribed_to_events", count=len(event_types))
            except Exception as e:
                logger.error("failed_to_subscribe_to_events", error=str(e))
        
        # Main event processing loop
        try:
            while self.running:
                try:
                    # Process queued events with timeout
                    await asyncio.wait_for(self._process_event_queue(), timeout=5.0)
                except asyncio.TimeoutError:
                    # No events for 5 seconds - continue loop
                    pass
        except Exception as e:
            logger.error("training_loop_error", error=str(e))
        finally:
            logger.info("training_loop_stopped")
    
    async def stop(self) -> None:
        """Stop the training loop gracefully"""
        self.running = False
        # Persist learned rules on shutdown
        self.learning_engine.persist_learned_rules()
        logger.info("training_loop_shutdown", 
                   stats=self.learning_engine.get_stats())
    
    def on_event(self, event_data: Dict[str, Any]) -> None:
        """
        Called when system event occurs.
        Queue event for async processing.
        """
        try:
            # Add to event queue (non-blocking)
            self.event_queue.put_nowait(event_data)
        except Exception as e:
            logger.error("failed_to_queue_event", error=str(e))
    
    async def _process_event_queue(self) -> None:
        """Process all queued events"""
        try:
            # Get event with timeout
            event_data = self.event_queue.get_nowait()
            
            # Extract event details
            event_type = event_data.get('event_type', 'unknown')
            
            # Make decision
            decision = self.decision_engine.evaluate_event(event_type, event_data)
            
            # Record decision in learning engine
            self.learning_engine.record_decision(decision)
            
            # Send to operator shell for display
            if self.operator_shell:
                try:
                    self.operator_shell.add_decision({
                        'timestamp': datetime.fromtimestamp(decision.timestamp).isoformat(),
                        'type': decision.action.value,
                        'details': decision.reasoning
                    })
                except Exception as e:
                    logger.error("failed_to_send_decision_to_shell", error=str(e))
            
            # Store experience in memory bridge
            if self.memory_bridge:
                try:
                    # Store as episodic event
                    self.memory_bridge.epi.write_event({
                        'kind': 'training_decision',
                        'decision_id': decision.decision_id,
                        'event_type': event_type,
                        'action': decision.action.value,
                        'confidence': decision.confidence,
                        'ts': decision.timestamp
                    })
                except Exception as e:
                    logger.error("failed_to_store_experience", error=str(e))
            
            # If action is ASK_USER, wait for feedback
            if decision.action == ActionType.ASK_USER:
                # In real implementation, this would be handled by GUI
                logger.info("awaiting_user_feedback", decision_id=decision.decision_id)
        
        except asyncio.QueueEmpty:
            pass
    
    def set_autonomy_level(self, level: int) -> None:
        """Update autonomy level (1-5)"""
        if 1 <= level <= 5:
            self.autonomy_level = level
            self.decision_engine.set_autonomy_level(level)
            logger.info("autonomy_level_updated", level=level)
    
    def provide_feedback(self, decision_id: str, feedback: str, 
                        user_override: Optional[str] = None) -> None:
        """
        Provide user feedback on a decision.
        
        Args:
            decision_id: ID of decision to provide feedback on
            feedback: "approve", "reject", "timeout", or "override"
            user_override: If override, what should have happened instead
        """
        try:
            feedback_type = FeedbackType[feedback.upper()]
            self.learning_engine.record_feedback(decision_id, feedback_type, user_override)
            
            # Periodically persist learned rules
            if len(self.learning_engine.decision_history) % 10 == 0:
                self.learning_engine.persist_learned_rules()
        except KeyError:
            logger.error("invalid_feedback_type", feedback=feedback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training loop statistics"""
        return {
            'running': self.running,
            'autonomy_level': self.autonomy_level,
            'learning': self.learning_engine.get_stats(),
            'event_queue_size': self.event_queue.qsize()
        }


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Test decision engine
    engine = DecisionEngine()
    
    # Test event: file created on Desktop
    test_event = {
        'path': 'C:\\Users\\User\\Desktop\\suspicious.exe',
        'size': 1024
    }
    
    print("\n=== Testing Decision Engine ===")
    print(f"Autonomy Level: {engine.current_autonomy_level}")
    
    decision = engine.evaluate_event('file_created', test_event)
    print(f"Decision: {decision.action.value}")
    print(f"Confidence: {decision.confidence}")
    print(f"Reasoning: {decision.reasoning}")
    
    # Test learning
    learning = LearningEngine()
    learning.record_decision(decision)
    print(f"\nLearning Engine Stats: {learning.get_stats()}")
