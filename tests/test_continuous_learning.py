"""
Test Phase 7: Continuous Learning Infrastructure

Validates online learning from execution feedback:
- Feedback recording and history
- Mode preference learning
- Pattern weight adaptation
- Intent-to-mode mapping
- Cognitive graph weight updates
- Performance metrics tracking
- Policy export/import
"""

from chat_os.cognitive.continuous_learning import (
    ContinuousLearner,
    ExecutionFeedback,
    FeedbackType,
    OutcomeType,
    get_learner,
)
from chat_os.cognitive.meta_controller import ReasoningMode


def test_feedback_creation():
    """ExecutionFeedback creates with valid attributes."""
    feedback = ExecutionFeedback(
        task_id="test_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        execution_time=0.5,
        quality_score=0.9,
    )

    assert feedback.task_id == "test_001"
    assert feedback.outcome == OutcomeType.SUCCESS
    assert feedback.feedback_type == FeedbackType.TASK_OUTCOME
    assert feedback.reasoning_mode == ReasoningMode.SYMBOLIC
    assert feedback.execution_time == 0.5
    assert feedback.quality_score == 0.9
    assert feedback.timestamp > 0


def test_learner_initialization():
    """ContinuousLearner initializes correctly."""
    learner = ContinuousLearner(learning_rate=0.2, memory_size=500)

    assert learner.learning_rate == 0.2
    assert learner.memory_size == 500
    assert len(learner.feedback_history) == 0
    assert learner.stats.total_feedback == 0


def test_record_feedback():
    """Learner records feedback and updates stats."""
    learner = ContinuousLearner()

    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
    )

    learner.record_feedback(feedback)

    assert learner.stats.total_feedback == 1
    assert learner.stats.success_count == 1
    assert len(learner.feedback_history) == 1


def test_mode_preference_learning():
    """Learner updates mode preferences based on success."""
    learner = ContinuousLearner(learning_rate=0.5)

    # Success with DEDUCTIVE mode
    feedback1 = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
    )
    learner.record_feedback(feedback1)

    # Check preference increased
    assert "symbolic" in learner.mode_preferences
    assert learner.mode_preferences["symbolic"] > 0.5  # Above neutral

    # Failure with INDUCTIVE mode
    feedback2 = ExecutionFeedback(
        task_id="task_002",
        outcome=OutcomeType.FAILURE,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.STATISTICAL,
    )
    learner.record_feedback(feedback2)

    # Check preference decreased
    assert "statistical" in learner.mode_preferences
    assert learner.mode_preferences["statistical"] < 0.5  # Below neutral


def test_mode_statistics():
    """Learner tracks mode success rates and times."""
    learner = ContinuousLearner()

    # Record multiple outcomes for DEDUCTIVE
    for i in range(5):
        outcome = OutcomeType.SUCCESS if i < 3 else OutcomeType.FAILURE
        feedback = ExecutionFeedback(
            task_id=f"task_{i}",
            outcome=outcome,
            feedback_type=FeedbackType.TASK_OUTCOME,
            reasoning_mode=ReasoningMode.SYMBOLIC,
            execution_time=0.1 * (i + 1),
        )
        learner.record_feedback(feedback)

    # Check statistics
    assert learner.stats.mode_usage_counts["symbolic"] == 5
    assert 0.0 < learner.stats.mode_success_rates["symbolic"] < 1.0
    assert learner.stats.mode_avg_times["symbolic"] > 0


def test_pattern_weight_learning():
    """Learner adapts pattern weights based on success."""
    learner = ContinuousLearner(learning_rate=0.3)

    # Success with pattern "file_read"
    feedback1 = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.PATTERN_MATCH,
        metadata={"patterns": ["file_read"]},
    )
    learner.record_feedback(feedback1)

    # Check pattern weight increased
    assert "file_read" in learner.pattern_weights
    assert learner.pattern_weights["file_read"] > 0.5

    # Failure with pattern "api_call"
    feedback2 = ExecutionFeedback(
        task_id="task_002",
        outcome=OutcomeType.FAILURE,
        feedback_type=FeedbackType.PATTERN_MATCH,
        metadata={"patterns": ["api_call"]},
    )
    learner.record_feedback(feedback2)

    # Check pattern weight decreased
    assert "api_call" in learner.pattern_weights
    assert learner.pattern_weights["api_call"] < 0.5


def test_intent_mode_mapping():
    """Learner learns intent-to-mode mappings."""
    learner = ContinuousLearner()

    # Successful query → DEDUCTIVE mapping
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        intent_type="query",
        intent_domain="code",
    )
    learner.record_feedback(feedback)

    # Check mapping learned
    assert ("query", "code") in learner.intent_mode_mapping
    assert learner.intent_mode_mapping[("query", "code")] == "symbolic"


def test_recommend_mode():
    """Learner recommends modes based on learned patterns."""
    learner = ContinuousLearner()

    # Train with successful pattern
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        intent_type="query",
        intent_domain="code",
    )
    learner.record_feedback(feedback)

    # Get recommendation
    recommended = learner.recommend_mode("query", "code")
    assert recommended == ReasoningMode.SYMBOLIC


def test_recommend_mode_no_data():
    """Learner returns None when no recommendation available."""
    learner = ContinuousLearner()

    recommended = learner.recommend_mode("unknown_intent", "unknown_domain")
    assert recommended is None


def test_pattern_confidence():
    """Learner reports pattern confidence."""
    learner = ContinuousLearner()

    # Default confidence
    conf1 = learner.get_pattern_confidence("new_pattern")
    assert conf1 == 0.5  # Neutral

    # After success
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.PATTERN_MATCH,
        metadata={"patterns": ["test_pattern"]},
    )
    learner.record_feedback(feedback)

    conf2 = learner.get_pattern_confidence("test_pattern")
    assert conf2 > 0.5  # Increased


def test_mode_performance_metrics():
    """Learner provides mode performance metrics."""
    learner = ContinuousLearner()

    # Record some feedback
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        execution_time=0.5,
    )
    learner.record_feedback(feedback)

    # Get performance
    perf = learner.get_mode_performance(ReasoningMode.SYMBOLIC)

    assert "success_rate" in perf
    assert "avg_time" in perf
    assert "usage_count" in perf
    assert "preference" in perf
    assert perf["usage_count"] == 1


def test_learning_stats():
    """Learner provides overall statistics."""
    learner = ContinuousLearner()

    # Record mixed outcomes
    feedback1 = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
    )
    feedback2 = ExecutionFeedback(
        task_id="task_002",
        outcome=OutcomeType.FAILURE,
        feedback_type=FeedbackType.TASK_OUTCOME,
        correction="User corrected output",
    )

    learner.record_feedback(feedback1)
    learner.record_feedback(feedback2)

    stats = learner.get_learning_stats()

    assert stats.total_feedback == 2
    assert stats.success_count == 1
    assert stats.failure_count == 1
    assert stats.correction_count == 1


def test_recent_feedback():
    """Learner returns recent feedback entries."""
    learner = ContinuousLearner()

    # Record multiple feedback
    for i in range(5):
        feedback = ExecutionFeedback(
            task_id=f"task_{i}",
            outcome=OutcomeType.SUCCESS,
            feedback_type=FeedbackType.TASK_OUTCOME,
        )
        learner.record_feedback(feedback)

    # Get recent (newest first)
    recent = learner.get_recent_feedback(limit=3)

    assert len(recent) == 3
    assert recent[0].task_id == "task_4"  # Newest
    assert recent[2].task_id == "task_2"  # Oldest in window


def test_memory_limit():
    """Learner respects memory size limit."""
    learner = ContinuousLearner(memory_size=10)

    # Record more than limit
    for i in range(15):
        feedback = ExecutionFeedback(
            task_id=f"task_{i}",
            outcome=OutcomeType.SUCCESS,
            feedback_type=FeedbackType.TASK_OUTCOME,
        )
        learner.record_feedback(feedback)

    # Check history trimmed
    assert len(learner.feedback_history) == 10
    # Oldest entries removed
    assert learner.feedback_history[0].task_id == "task_5"


def test_reset_learning():
    """Learner can reset all learned patterns."""
    learner = ContinuousLearner()

    # Record feedback and learn patterns
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
    )
    learner.record_feedback(feedback)

    assert learner.stats.total_feedback > 0
    assert len(learner.mode_preferences) > 0

    # Reset
    learner.reset_learning()

    assert learner.stats.total_feedback == 0
    assert len(learner.mode_preferences) == 0
    assert len(learner.feedback_history) == 0


def test_export_policies():
    """Learner exports learned policies."""
    learner = ContinuousLearner()

    # Learn some patterns
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        intent_type="query",
        intent_domain="code",
        metadata={"patterns": ["test_pattern"]},
    )
    learner.record_feedback(feedback)

    # Export
    policies = learner.export_learned_policies()

    assert "mode_preferences" in policies
    assert "pattern_weights" in policies
    assert "intent_mode_mapping" in policies
    assert "stats" in policies

    # Check content
    assert "symbolic" in policies["mode_preferences"]
    assert "test_pattern" in policies["pattern_weights"]


def test_import_policies():
    """Learner imports previously learned policies."""
    learner1 = ContinuousLearner()

    # Learn patterns
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
        intent_type="query",
        intent_domain="code",
    )
    learner1.record_feedback(feedback)

    # Export
    policies = learner1.export_learned_policies()

    # Create new learner and import
    learner2 = ContinuousLearner()
    learner2.import_learned_policies(policies)

    # Check imported
    assert learner2.mode_preferences == learner1.mode_preferences
    assert learner2.intent_mode_mapping == learner1.intent_mode_mapping
    assert learner2.stats.total_feedback == learner1.stats.total_feedback


def test_cognitive_graph_update():
    """Learner updates cognitive graph edge weights."""
    from chat_os.cognitive.cognitive_graph import EdgeType, NodeType, get_cognitive_graph

    graph = get_cognitive_graph()
    graph.clear()  # Start fresh

    # Create nodes
    node_a = graph.add_node(NodeType.CONCEPT, "A")
    node_b = graph.add_node(NodeType.CONCEPT, "B")

    # Create edge
    edge = graph.add_edge([node_a], [node_b], EdgeType.IMPLIES, weight=0.5)
    initial_weight = edge.weight

    # Record successful feedback involving these nodes
    learner = ContinuousLearner(learning_rate=0.3)
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        metadata={
            "source_nodes": [node_a.node_id],
            "target_nodes": [node_b.node_id],
        },
    )
    learner.record_feedback(feedback)

    # Check weight increased
    assert edge.weight > initial_weight
    assert learner.stats.edge_weight_updates > 0


def test_outcome_types():
    """OutcomeType enum has all expected types."""
    expected = ["SUCCESS", "FAILURE", "PARTIAL", "TIMEOUT", "ERROR", "CANCELLED"]
    for outcome_name in expected:
        assert hasattr(OutcomeType, outcome_name)


def test_feedback_types():
    """FeedbackType enum has all expected types."""
    expected = [
        "TASK_OUTCOME",
        "USER_CORRECTION",
        "PERFORMANCE_METRIC",
        "QUALITY_METRIC",
        "PATTERN_MATCH",
    ]
    for feedback_name in expected:
        assert hasattr(FeedbackType, feedback_name)


def test_global_singleton():
    """get_learner returns singleton."""
    learner1 = get_learner()
    learner2 = get_learner()

    assert learner1 is learner2
    assert isinstance(learner1, ContinuousLearner)


def test_learning_rate_effect():
    """Higher learning rate causes faster adaptation."""
    learner_slow = ContinuousLearner(learning_rate=0.1)
    learner_fast = ContinuousLearner(learning_rate=0.9)

    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
    )

    learner_slow.record_feedback(feedback)
    learner_fast.record_feedback(feedback)

    # Fast learner should have higher preference change
    slow_pref = learner_slow.mode_preferences["symbolic"]
    fast_pref = learner_fast.mode_preferences["symbolic"]

    assert fast_pref > slow_pref


def test_partial_outcome():
    """Learner handles partial success appropriately."""
    learner = ContinuousLearner(learning_rate=0.5)

    # Partial outcome (neutral reward)
    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.PARTIAL,
        feedback_type=FeedbackType.TASK_OUTCOME,
        reasoning_mode=ReasoningMode.SYMBOLIC,
    )
    learner.record_feedback(feedback)

    # Preference should be near neutral (0.5)
    pref = learner.mode_preferences["symbolic"]
    assert 0.4 < pref < 0.6  # Near neutral


def test_multiple_patterns():
    """Learner handles multiple patterns in single feedback."""
    learner = ContinuousLearner()

    feedback = ExecutionFeedback(
        task_id="task_001",
        outcome=OutcomeType.SUCCESS,
        feedback_type=FeedbackType.PATTERN_MATCH,
        metadata={"patterns": ["pattern_a", "pattern_b", "pattern_c"]},
    )
    learner.record_feedback(feedback)

    # All patterns should be learned
    assert "pattern_a" in learner.pattern_weights
    assert "pattern_b" in learner.pattern_weights
    assert "pattern_c" in learner.pattern_weights


# Phase 7 Complete: 25 tests validating continuous learning
