"""
Tests for ASTRA Planner L2 System
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from astra.core.planner_l2 import (
    PlanGenerator,
    ConsentManager,
    PlanExecutor,
    PlannerL2,
    PlanStep,
    ExecutionPlan,
    StepStatus,
    RiskLevel,
)
from astra.core.event_bus import get_event_bus

# ============================================================================
# MOCKS & FIXTURES
# ============================================================================


class MockLLM:
    """Mock LLM for testing"""

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        return """
        - Description: Step 1 description
          Tool: tool1
          Action: action1
          Risk: low
        
        - Description: Step 2 description
          Tool: tool2
          Action: action2
          Risk: high
        """


class MockToolRegistry:
    """Mock tool registry"""

    def execute(self, tool: str, action: str, args: dict):
        return f"Result from {tool}.{action}"


class EventCollector:
    """Collect emitted events"""

    def __init__(self):
        self.events = []

    def collect(self, event):
        self.events.append(event)


# ============================================================================
# PLAN GENERATOR TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_plan_generator_creation():
    """Test plan generator initialization"""
    llm = MockLLM()
    registry = MockToolRegistry()
    generator = PlanGenerator(llm, registry)

    assert generator.llm is llm
    assert generator.tool_registry is registry
    assert generator.plan_counter == 0


@pytest.mark.asyncio
async def test_plan_generation_basic():
    """Test basic plan generation"""
    llm = MockLLM()
    registry = MockToolRegistry()
    generator = PlanGenerator(llm, registry)

    plan = await generator.generate(
        "Do something", {"context": "test"}, max_steps=5, budget_tokens=20
    )

    assert plan.objective == "Do something"
    assert len(plan.steps) > 0
    assert plan.total_cost > 0
    assert not plan.is_expired()
    assert not plan.approved


@pytest.mark.asyncio
async def test_plan_step_cost_estimation():
    """Test cost estimation for plan steps"""
    llm = MockLLM()
    registry = MockToolRegistry()
    generator = PlanGenerator(llm, registry)

    # Test cost for different risk levels
    costs = {
        RiskLevel.LOW: generator._estimate_cost(
            PlanStep("s1", "desc", "tool", "action", {}, RiskLevel.LOW, 0)
        ),
        RiskLevel.HIGH: generator._estimate_cost(
            PlanStep("s2", "desc", "tool", "action", {}, RiskLevel.HIGH, 0)
        ),
        RiskLevel.CRITICAL: generator._estimate_cost(
            PlanStep("s3", "desc", "tool", "action", {}, RiskLevel.CRITICAL, 0)
        ),
    }

    # High risk should cost more than low risk
    assert costs[RiskLevel.HIGH] > costs[RiskLevel.LOW]
    assert costs[RiskLevel.CRITICAL] > costs[RiskLevel.HIGH]


@pytest.mark.asyncio
async def test_plan_expiration():
    """Test plan expiration checking"""
    llm = MockLLM()
    registry = MockToolRegistry()
    generator = PlanGenerator(llm, registry)

    plan = await generator.generate("Test objective", {}, max_steps=5, budget_tokens=20)

    # Fresh plan should not be expired
    assert not plan.is_expired()

    # Manually set expiration to past
    plan.expires_at = datetime.now() - timedelta(seconds=1)
    assert plan.is_expired()


# ============================================================================
# CONSENT MANAGER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_consent_manager_creation():
    """Test consent manager initialization"""
    manager = ConsentManager()

    assert manager.callback is None
    assert len(manager.pending_requests) == 0
    assert len(manager.approvals) == 0


@pytest.mark.asyncio
async def test_consent_approval_flow():
    """Test basic consent approval"""
    bus = get_event_bus()
    collector = EventCollector()
    bus.subscribe("astra.plan.consent_requested", collector.collect)
    bus.subscribe("astra.plan.consent_decision", collector.collect)

    manager = ConsentManager()

    # Create simple plan
    plan = ExecutionPlan(
        id="plan1",
        objective="Test",
        steps=[],
        total_cost=2,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Request approval (should auto-approve low-cost)
    approved = await manager.request_approval(plan)

    assert approved is True
    assert plan.id in manager.approvals
    assert manager.approvals[plan.id] is True

    # Check events
    assert len(collector.events) >= 2
    assert collector.events[0].name == "astra.plan.consent_requested"
    assert collector.events[1].name == "astra.plan.consent_decision"


@pytest.mark.asyncio
async def test_consent_rejection_high_cost():
    """Test consent rejection for high-cost plans"""
    manager = ConsentManager()

    # Create high-cost plan (should auto-reject)
    plan = ExecutionPlan(
        id="plan2",
        objective="Expensive operation",
        steps=[],
        total_cost=100,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
    )

    approved = await manager.request_approval(plan, timeout_s=1)

    assert approved is False
    assert manager.approvals[plan.id] is False


@pytest.mark.asyncio
async def test_consent_callback():
    """Test consent with callback"""
    approval_value = True

    def approval_callback(plan):
        return approval_value

    manager = ConsentManager(approval_callback)

    plan = ExecutionPlan(
        id="plan3",
        objective="With callback",
        steps=[],
        total_cost=10,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Test approval
    approved = await manager.request_approval(plan, timeout_s=5)
    assert approved is True

    # Test rejection
    approval_value = False
    plan2 = ExecutionPlan(
        id="plan4",
        objective="With callback 2",
        steps=[],
        total_cost=10,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
    )

    approved = await manager.request_approval(plan2, timeout_s=5)
    assert approved is False


# ============================================================================
# PLAN EXECUTOR TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_plan_executor_initialization():
    """Test executor initialization"""
    registry = MockToolRegistry()
    bus = get_event_bus()
    executor = PlanExecutor(registry, bus)

    assert executor.tool_registry is registry
    assert executor.event_bus is bus


@pytest.mark.asyncio
async def test_plan_executor_not_approved():
    """Test execution of unapproved plan"""
    registry = MockToolRegistry()
    bus = get_event_bus()
    executor = PlanExecutor(registry, bus)

    plan = ExecutionPlan(
        id="plan5",
        objective="Not approved",
        steps=[],
        total_cost=5,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
        approved=False,
    )

    success = await executor.execute(plan, 20)
    assert success is False


@pytest.mark.asyncio
async def test_plan_executor_expired():
    """Test execution of expired plan"""
    registry = MockToolRegistry()
    bus = get_event_bus()
    executor = PlanExecutor(registry, bus)

    plan = ExecutionPlan(
        id="plan6",
        objective="Expired",
        steps=[],
        total_cost=5,
        created_at=datetime.now(),
        expires_at=datetime.now() - timedelta(seconds=1),
        approved=True,
    )

    success = await executor.execute(plan, 20)
    assert success is False


@pytest.mark.asyncio
async def test_plan_executor_budget_exhaustion():
    """Test execution stops when budget exhausted"""
    registry = MockToolRegistry()
    bus = get_event_bus()
    executor = PlanExecutor(registry, bus)

    # Create plan with expensive step
    step1 = PlanStep(
        id="s1",
        description="Expensive step",
        tool="tool1",
        action="action1",
        args={},
        risk_level=RiskLevel.LOW,
        cost_estimate=15,
    )
    step2 = PlanStep(
        id="s2",
        description="Another step",
        tool="tool2",
        action="action2",
        args={},
        risk_level=RiskLevel.LOW,
        cost_estimate=10,
    )

    plan = ExecutionPlan(
        id="plan7",
        objective="Budget exhaustion test",
        steps=[step1, step2],
        total_cost=25,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
        approved=True,
    )

    # Only 10 tokens budget (can't afford both steps)
    success = await executor.execute(plan, 10)

    # Should skip first step (15 > 10), execute second (10 == 10)
    assert step1.status == StepStatus.SKIPPED
    assert step2.status in [StepStatus.SUCCESS, StepStatus.FAILED]


# ============================================================================
# PLANNER L2 ORCHESTRATOR TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_planner_l2_initialization():
    """Test Planner L2 initialization"""
    llm = MockLLM()
    registry = MockToolRegistry()

    planner = PlannerL2(llm, registry)

    assert planner.llm is llm
    assert planner.tool_registry is registry
    assert planner.generator is not None
    assert planner.consent_mgr is not None
    assert planner.executor is not None


@pytest.mark.asyncio
async def test_planner_l2_full_workflow():
    """Test complete Plan->Ask->Act workflow"""
    bus = get_event_bus()
    collector = EventCollector()

    # Collect all events
    bus.subscribe("astra.plan.execution_start", collector.collect)
    bus.subscribe("astra.plan.execution_complete", collector.collect)
    bus.subscribe("astra.plan.consent_requested", collector.collect)
    bus.subscribe("astra.plan.consent_decision", collector.collect)

    llm = MockLLM()
    registry = MockToolRegistry()
    planner = PlannerL2(llm, registry)

    success = await planner.execute_objective(
        "Complete test objective", {"test": "context"}, budget_tokens=20, max_steps=5
    )

    # Should succeed with low-cost plan
    assert success is True

    # Check events were emitted
    event_names = [e.name for e in collector.events]
    assert "astra.plan.consent_requested" in event_names
    assert "astra.plan.consent_decision" in event_names
    assert "astra.plan.execution_start" in event_names
    assert "astra.plan.execution_complete" in event_names


@pytest.mark.asyncio
async def test_planner_l2_rejection():
    """Test objective rejection"""

    def reject_callback(plan):
        return False  # Always reject

    llm = MockLLM()
    registry = MockToolRegistry()
    planner = PlannerL2(llm, registry, reject_callback)

    success = await planner.execute_objective(
        "Will be rejected", {}, budget_tokens=100, max_steps=5
    )

    assert success is False


@pytest.mark.asyncio
async def test_planner_l2_context_propagation():
    """Test context is properly propagated"""
    llm = MockLLM()
    registry = MockToolRegistry()
    planner = PlannerL2(llm, registry)

    context = {"user": "test_user", "env": "test", "trace_id": "123abc"}

    success = await planner.execute_objective("Context test", context, budget_tokens=20)

    assert success is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_remaining_cost_calculation():
    """Test remaining cost calculation"""
    step1 = PlanStep(
        id="s1",
        description="desc1",
        tool="tool1",
        action="action1",
        args={},
        risk_level=RiskLevel.LOW,
        cost_estimate=5,
    )
    step2 = PlanStep(
        id="s2",
        description="desc2",
        tool="tool2",
        action="action2",
        args={},
        risk_level=RiskLevel.MEDIUM,
        cost_estimate=10,
    )

    plan = ExecutionPlan(
        id="p1",
        objective="Cost test",
        steps=[step1, step2],
        total_cost=15,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Initially all steps remaining
    assert plan.remaining_cost() == 15

    # After executing first step
    plan.executed_steps = 1
    assert plan.remaining_cost() == 10

    # After executing both
    plan.executed_steps = 2
    assert plan.remaining_cost() == 0
