"""
Phase 7: Continuous Learning Infrastructure

Enables online learning from execution feedback:
- Learn from task outcomes (success/failure)
- Update operator selection policies
- Adapt emotional response heuristics
- Refine pattern recognition
- Evolve cognitive graph weights
- Track performance metrics over time
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chat_os.cognitive.cognitive_graph import get_cognitive_graph
from chat_os.cognitive.meta_controller import ReasoningMode


class OutcomeType(Enum):
    """Task outcome classification."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"


class FeedbackType(Enum):
    """Type of learning signal."""

    TASK_OUTCOME = "task_outcome"  # Task succeeded/failed
    USER_CORRECTION = "user_correction"  # User corrected output
    PERFORMANCE_METRIC = "performance_metric"  # Speed, resource usage
    QUALITY_METRIC = "quality_metric"  # Output quality assessment
    PATTERN_MATCH = "pattern_match"  # Pattern recognition accuracy


@dataclass
class ExecutionFeedback:
    """
    Feedback from a task execution.

    Contains outcome, metrics, and context for learning.
    """

    task_id: str
    outcome: OutcomeType
    feedback_type: FeedbackType
    timestamp: float = field(default_factory=time.time)

    # Context
    reasoning_mode: ReasoningMode | None = None
    operator_id: str | None = None
    intent_type: str | None = None
    intent_domain: str | None = None

    # Metrics
    execution_time: float = 0.0  # seconds
    resource_usage: dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.0  # [0-1]
    confidence: float = 0.0  # [0-1]

    # Learning signals
    error_message: str | None = None
    correction: str | None = None  # User's correction
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningStats:
    """Statistics about learned patterns."""

    total_feedback: int = 0
    success_count: int = 0
    failure_count: int = 0
    correction_count: int = 0

    # Per-mode statistics
    mode_success_rates: dict[str, float] = field(default_factory=dict)
    mode_avg_times: dict[str, float] = field(default_factory=dict)
    mode_usage_counts: dict[str, int] = field(default_factory=dict)

    # Pattern evolution
    pattern_confidence: dict[str, float] = field(default_factory=dict)
    edge_weight_updates: int = 0
    learning_rate: float = 0.1


class ContinuousLearner:
    """
    Continuous learning system.

    Learns from execution feedback to improve:
    - Reasoning mode selection
    - Emotional response heuristics
    - Pattern recognition confidence
    - Cognitive graph edge weights
    """

    def __init__(self, learning_rate: float = 0.1, memory_size: int = 1000):
        """
        Initialize continuous learner.

        Args:
            learning_rate: How quickly to adapt [0-1]
            memory_size: Max feedback history to retain
        """
        self.learning_rate = learning_rate
        self.memory_size = memory_size

        self.feedback_history: list[ExecutionFeedback] = []
        self.stats = LearningStats(learning_rate=learning_rate)

        # Learned policies
        self.mode_preferences: dict[str, float] = {}  # Mode → preference score
        self.pattern_weights: dict[str, float] = {}  # Pattern → confidence
        self.intent_mode_mapping: dict[tuple[str, str], str] = (
            {}
        )  # (intent_type, domain) → mode

    def record_feedback(self, feedback: ExecutionFeedback) -> None:
        """
        Record execution feedback for learning.

        Args:
            feedback: Execution outcome and metrics
        """
        self.feedback_history.append(feedback)
        self.stats.total_feedback += 1

        # Update outcome counts
        if feedback.outcome == OutcomeType.SUCCESS:
            self.stats.success_count += 1
        elif feedback.outcome == OutcomeType.FAILURE:
            self.stats.failure_count += 1

        if feedback.correction:
            self.stats.correction_count += 1

        # Trim history if too large
        if len(self.feedback_history) > self.memory_size:
            self.feedback_history = self.feedback_history[-self.memory_size :]

        # Learn from feedback
        self._update_mode_preferences(feedback)
        self._update_pattern_weights(feedback)
        self._update_intent_mapping(feedback)
        self._update_cognitive_graph(feedback)

    def _update_mode_preferences(self, feedback: ExecutionFeedback) -> None:
        """Update reasoning mode preferences based on success."""
        if not feedback.reasoning_mode:
            return

        mode = feedback.reasoning_mode.name.lower()  # Use name (string) not value (int)

        # Initialize if needed
        if mode not in self.mode_preferences:
            self.mode_preferences[mode] = 0.5  # Neutral

        # Update based on outcome
        if feedback.outcome == OutcomeType.SUCCESS:
            reward = 1.0
        elif feedback.outcome == OutcomeType.PARTIAL:
            reward = 0.5
        else:
            reward = 0.0

        # Apply learning rate
        current = self.mode_preferences[mode]
        self.mode_preferences[mode] = current + self.learning_rate * (reward - current)

        # Update statistics
        if mode not in self.stats.mode_success_rates:
            self.stats.mode_success_rates[mode] = 0.0
            self.stats.mode_avg_times[mode] = 0.0
            self.stats.mode_usage_counts[mode] = 0

        self.stats.mode_usage_counts[mode] += 1
        count = self.stats.mode_usage_counts[mode]

        # Update success rate (running average)
        old_rate = self.stats.mode_success_rates[mode]
        success = 1.0 if feedback.outcome == OutcomeType.SUCCESS else 0.0
        self.stats.mode_success_rates[mode] = old_rate + (success - old_rate) / count

        # Update average time
        old_time = self.stats.mode_avg_times[mode]
        self.stats.mode_avg_times[mode] = (
            old_time + (feedback.execution_time - old_time) / count
        )

    def _update_pattern_weights(self, feedback: ExecutionFeedback) -> None:
        """Update pattern recognition weights."""
        # Extract patterns from metadata
        patterns = feedback.metadata.get("patterns", [])

        for pattern in patterns:
            if pattern not in self.pattern_weights:
                self.pattern_weights[pattern] = 0.5

            # Increase weight on success, decrease on failure
            if feedback.outcome == OutcomeType.SUCCESS:
                adjustment = self.learning_rate * (1.0 - self.pattern_weights[pattern])
            else:
                adjustment = -self.learning_rate * self.pattern_weights[pattern]

            self.pattern_weights[pattern] += adjustment
            self.stats.pattern_confidence[pattern] = self.pattern_weights[pattern]

    def _update_intent_mapping(self, feedback: ExecutionFeedback) -> None:
        """Learn intent → reasoning mode mapping."""
        if not feedback.intent_type or not feedback.reasoning_mode:
            return

        intent_key = (
            feedback.intent_type,
            feedback.intent_domain or "unknown",
        )

        # On success, reinforce mapping (store name not value)
        if feedback.outcome == OutcomeType.SUCCESS:
            self.intent_mode_mapping[intent_key] = feedback.reasoning_mode.name.lower()

    def _update_cognitive_graph(self, feedback: ExecutionFeedback) -> None:
        """Update cognitive graph edge weights based on feedback."""
        graph = get_cognitive_graph()

        # Extract nodes involved in reasoning
        source_nodes = feedback.metadata.get("source_nodes", [])
        target_nodes = feedback.metadata.get("target_nodes", [])

        if not source_nodes or not target_nodes:
            return

        # Find edges between these nodes
        for edge in graph.edges.values():
            if (
                any(n in edge.source_nodes for n in source_nodes)
                and any(n in edge.target_nodes for n in target_nodes)
            ):
                # Adjust weight based on outcome
                if feedback.outcome == OutcomeType.SUCCESS:
                    # Strengthen successful reasoning paths
                    new_weight = edge.weight + self.learning_rate * (1.0 - edge.weight)
                elif feedback.outcome == OutcomeType.FAILURE:
                    # Weaken failed reasoning paths
                    new_weight = edge.weight - self.learning_rate * edge.weight
                else:
                    continue

                # Clamp to [0, 1]
                edge.weight = max(0.0, min(1.0, new_weight))
                self.stats.edge_weight_updates += 1

    def recommend_mode(
        self, intent_type: str, intent_domain: str | None = None
    ) -> ReasoningMode | None:
        """
        Recommend reasoning mode based on learned patterns.

        Args:
            intent_type: Type of intent
            intent_domain: Domain of intent

        Returns:
            Recommended reasoning mode, or None if no recommendation
        """
        intent_key = (intent_type, intent_domain or "unknown")

        # Check learned mapping
        if intent_key in self.intent_mode_mapping:
            mode_str = self.intent_mode_mapping[intent_key]
            try:
                return ReasoningMode[mode_str.upper()]  # Convert to enum by name
            except (KeyError, AttributeError):
                pass

        # Fallback: highest preference mode
        if self.mode_preferences:
            best_mode = max(self.mode_preferences.items(), key=lambda x: x[1])
            if best_mode[1] > 0.6:  # Only recommend if confident
                try:
                    return ReasoningMode[best_mode[0].upper()]
                except (KeyError, AttributeError):
                    pass

        return None

    def get_pattern_confidence(self, pattern: str) -> float:
        """
        Get confidence in a pattern.

        Args:
            pattern: Pattern identifier

        Returns:
            Confidence score [0-1]
        """
        return self.pattern_weights.get(pattern, 0.5)

    def get_mode_performance(self, mode: ReasoningMode) -> dict[str, float]:
        """
        Get performance metrics for a reasoning mode.

        Args:
            mode: Reasoning mode

        Returns:
            Dict with success_rate, avg_time, usage_count
        """
        mode_str = mode.name.lower()  # Use name not value

        return {
            "success_rate": self.stats.mode_success_rates.get(mode_str, 0.0),
            "avg_time": self.stats.mode_avg_times.get(mode_str, 0.0),
            "usage_count": self.stats.mode_usage_counts.get(mode_str, 0),
            "preference": self.mode_preferences.get(mode_str, 0.5),
        }

    def get_learning_stats(self) -> LearningStats:
        """Get overall learning statistics."""
        return self.stats

    def get_recent_feedback(self, limit: int = 10) -> list[ExecutionFeedback]:
        """
        Get recent feedback entries.

        Args:
            limit: Max number to return

        Returns:
            Recent feedback, newest first
        """
        return list(reversed(self.feedback_history[-limit:]))

    def reset_learning(self) -> None:
        """Reset all learned patterns (for testing or retraining)."""
        self.feedback_history.clear()
        self.stats = LearningStats(learning_rate=self.learning_rate)
        self.mode_preferences.clear()
        self.pattern_weights.clear()
        self.intent_mode_mapping.clear()

    def export_learned_policies(self) -> dict[str, Any]:
        """
        Export learned policies for persistence.

        Returns:
            Dict containing all learned patterns
        """
        return {
            "mode_preferences": self.mode_preferences.copy(),
            "pattern_weights": self.pattern_weights.copy(),
            "intent_mode_mapping": {
                f"{k[0]}:{k[1]}": v for k, v in self.intent_mode_mapping.items()
            },
            "stats": {
                "total_feedback": self.stats.total_feedback,
                "success_count": self.stats.success_count,
                "failure_count": self.stats.failure_count,
                "mode_success_rates": self.stats.mode_success_rates.copy(),
                "mode_avg_times": self.stats.mode_avg_times.copy(),
                "mode_usage_counts": self.stats.mode_usage_counts.copy(),
            },
        }

    def import_learned_policies(self, policies: dict[str, Any]) -> None:
        """
        Import previously learned policies.

        Args:
            policies: Exported policies dict
        """
        self.mode_preferences = policies.get("mode_preferences", {}).copy()
        self.pattern_weights = policies.get("pattern_weights", {}).copy()

        # Convert intent mapping keys back to tuples
        intent_mapping = policies.get("intent_mode_mapping", {})
        self.intent_mode_mapping = {
            tuple(k.split(":", 1)): v for k, v in intent_mapping.items()
        }

        # Import stats
        stats_data = policies.get("stats", {})
        self.stats.total_feedback = stats_data.get("total_feedback", 0)
        self.stats.success_count = stats_data.get("success_count", 0)
        self.stats.failure_count = stats_data.get("failure_count", 0)
        self.stats.mode_success_rates = stats_data.get("mode_success_rates", {}).copy()
        self.stats.mode_avg_times = stats_data.get("mode_avg_times", {}).copy()
        self.stats.mode_usage_counts = stats_data.get("mode_usage_counts", {}).copy()


# Global learner singleton
_learner: ContinuousLearner | None = None


def get_learner() -> ContinuousLearner:
    """Get global continuous learner singleton."""
    global _learner
    if _learner is None:
        _learner = ContinuousLearner()
    return _learner


# Example usage
if __name__ == "__main__":
    learner = get_learner()

    # Simulate feedback from successful task
    feedback1 = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        intent_type="query",
        intent_domain="code",
        execution_time=0.5,
        quality_score=0.9,
    )
    learner.record_feedback(feedback1)

    # Simulate feedback from failed task
    feedback2 = ExecutionFeedback(
        task_id="task_002",
        outcome=OutcomeType.FAILURE,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.STATISTICAL,
        intent_type="query",
        intent_domain="code",
        execution_time=1.2,
        error_message="Pattern not found",
    )
    learner.record_feedback(feedback2)

    # Get recommendation
    recommended = learner.recommend_mode("query", "code")
    print(f"Recommended mode for code query: {recommended}")

    # Get performance metrics
    symbolic_perf = learner.get_mode_performance(ReasoningMode.SYMBOLIC)
    print(f"\nSymbolic mode performance: {symbolic_perf}")

    # Get statistics
    stats = learner.get_learning_stats()
    print(f"\nLearning stats:")
    print(f"  Total feedback: {stats.total_feedback}")
    print(f"  Success rate: {stats.success_count / stats.total_feedback:.1%}")
    print(f"  Mode preferences: {learner.mode_preferences}")

    # Export and import
    policies = learner.export_learned_policies()
    print(f"\nExported policies: {len(policies)} categories")
