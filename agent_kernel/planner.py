# agent_kernel/planner.py
"""
ASTRA OS Agent Kernel - ReAct Planning Loop.
Implements IDLE → PLAN → CALL_TOOL → OBSERVE → (REFINE|ANSWER|ABORT) state machine.
"""
import json
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

from agent_kernel.memory import MemoryManager
from agent_kernel.tools import ToolRegistry
from telemetry.events import EventLogger
from telemetry.metrics import MetricsExporter


class AgentState(Enum):
    """Agent state machine states."""

    IDLE = "idle"
    PLAN = "plan"
    CALL_TOOL = "call_tool"
    OBSERVE = "observe"
    REFINE = "refine"
    ANSWER = "answer"
    ABORT = "abort"


class AgentKernel:
    """
    ReAct-style agent kernel with planning loop.
    Coordinates tool execution, memory, and event logging.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_func: Callable[[str], str] | None = None,
        max_iterations: int = 10,
        max_tool_calls: int = 20,
        loop_timeout_ms: int = 180000,
        event_logger: Callable[[dict], None] | None = None,
        memory_manager: MemoryManager | None = None,
        telemetry_logger: EventLogger | None = None,
        telemetry_metrics: MetricsExporter | None = None,
    ):
        """
        Initialize agent kernel.

        Args:
            tool_registry: Registry of available tools
            llm_func: LLM function for planning (prompt -> response)
            max_iterations: Max planning iterations before abort
            max_tool_calls: Max tool calls per loop
            loop_timeout_ms: Total loop timeout in milliseconds
            event_logger: Optional event logging callback (legacy)
            memory_manager: Optional memory manager for L0-L3 tiers
            telemetry_logger: Optional telemetry event logger
            telemetry_metrics: Optional telemetry metrics exporter
        """
        self.tools = tool_registry
        self.llm = llm_func or self._mock_llm
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.loop_timeout_ms = loop_timeout_ms
        self.event_logger = event_logger or self._default_logger

        # Memory and telemetry
        self.memory = memory_manager or MemoryManager()
        self.telemetry = telemetry_logger
        self.metrics = telemetry_metrics

        # State tracking
        self.state = AgentState.IDLE
        self.iteration = 0
        self.tool_calls = 0
        self.start_time_ms = 0.0
        self.context: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []

    def _default_logger(self, event: dict[str, Any]) -> None:
        """Default event logger (prints to stdout)."""
        print(f"[{event['event']}] {json.dumps(event, default=str)}")

    def _mock_llm(self, prompt: str) -> str:
        """Mock LLM for testing (returns help message)."""
        return "I need an actual LLM to plan actions. Use browser.navigate to start."

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log an event with timestamp."""
        event = {
            "event": event_type,
            "ts": time.time(),
            "iteration": self.iteration,
            **data,
        }
        self.event_logger(event)
        self.history.append(event)

    def _check_timeout(self) -> bool:
        """Check if loop timeout exceeded."""
        elapsed_ms = (time.perf_counter() * 1000) - self.start_time_ms
        return elapsed_ms > self.loop_timeout_ms

    def _check_budget(self) -> tuple[bool, str]:
        """
        Check if budgets are within limits.

        Returns:
            (ok, reason) tuple
        """
        if self.iteration >= self.max_iterations:
            return False, f"Max iterations ({self.max_iterations}) exceeded"

        if self.tool_calls >= self.max_tool_calls:
            return False, f"Max tool calls ({self.max_tool_calls}) exceeded"

        if self._check_timeout():
            return False, f"Loop timeout ({self.loop_timeout_ms}ms) exceeded"

        return True, ""

    def _transition(self, next_state: AgentState) -> None:
        """Transition to next state."""
        prev_state = self.state
        self.state = next_state
        self._log_event(
            "state.transition",
            {"from": prev_state.value, "to": next_state.value},
        )

        # Log to telemetry
        if self.telemetry:
            self.telemetry.log_state_transition(prev_state.value, next_state.value)
        if self.metrics:
            self.metrics.set_agent_state(next_state.value.upper())

    def _build_prompt(self, task: str) -> str:
        """
        Build planning prompt from task and history.

        Args:
            task: User task description

        Returns:
            Formatted prompt for LLM
        """
        # Get available tools
        tools = self.tools.list_tools()
        tool_desc = "\n".join(
            f"- {t['name']}: {t['description']}" for t in tools
        )

        # Format history
        history_text = ""
        for event in self.history[-5:]:  # Last 5 events
            if event["event"] == "tool.result":
                history_text += f"\nTool: {event['tool']}\nResult: {event.get('result', event.get('error'))}\n"

        prompt = f"""You are ASTRA OS, a sovereign AI agent. Plan the next action to complete this task:

TASK: {task}

AVAILABLE TOOLS:
{tool_desc}

HISTORY:
{history_text}

Respond with ONE of:
- CALL_TOOL: <tool_name> <json_args>
- ANSWER: <final_answer>
- REFINE: <clarification_question>

Your response:"""

        return prompt

    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into action.

        Args:
            response: LLM response text

        Returns:
            Dict with action, tool, args, or answer
        """
        response = response.strip()

        if response.startswith("CALL_TOOL:"):
            # Extract tool name and args
            parts = response[10:].strip().split(" ", 1)
            tool_name = parts[0]
            args = {}
            if len(parts) > 1:
                try:
                    args = json.loads(parts[1])
                except json.JSONDecodeError:
                    # Fallback: treat as single string arg
                    args = {"input": parts[1]}

            return {"action": "call_tool", "tool": tool_name, "args": args}

        elif response.startswith("ANSWER:"):
            answer = response[7:].strip()
            return {"action": "answer", "answer": answer}

        elif response.startswith("REFINE:"):
            question = response[7:].strip()
            return {"action": "refine", "question": question}

        else:
            # Default: treat as answer
            return {"action": "answer", "answer": response}

    def run(self, task: str) -> dict[str, Any]:
        """
        Run agent loop to complete task.

        Args:
            task: User task description

        Returns:
            Dict with ok, answer/error, iterations, tool_calls, elapsed_ms
        """
        self.start_time_ms = time.perf_counter() * 1000
        self.iteration = 0
        self.tool_calls = 0
        self.state = AgentState.IDLE
        self.context = {"task": task}
        self.history = []

        # Store task in session memory
        self.memory.write("session.task", task, tier="L1")
        self.memory.write("session.start_time", self.start_time_ms, tier="L1")

        self._log_event("agent.start", {"task": task})
        if self.telemetry:
            self.telemetry.log_agent_start(task)

        self._transition(AgentState.PLAN)

        try:
            while self.state not in (AgentState.ANSWER, AgentState.ABORT):
                # Check budgets
                ok, reason = self._check_budget()
                if not ok:
                    self._log_event("agent.abort", {"reason": reason})
                    self.context["error"] = reason  # Store abort reason
                    self._transition(AgentState.ABORT)
                    break

                # Execute current state
                if self.state == AgentState.PLAN:
                    self._execute_plan(task)
                elif self.state == AgentState.CALL_TOOL:
                    self._execute_tool()
                elif self.state == AgentState.OBSERVE:
                    self._execute_observe()
                elif self.state == AgentState.REFINE:
                    self._execute_refine()

                self.iteration += 1

                # Record metrics for iteration
                if self.metrics:
                    self.metrics.record_agent_iteration()

            # Extract result
            elapsed_ms = int((time.perf_counter() * 1000) - self.start_time_ms)

            # Clear loop memory (L2) after task completion
            self.memory.clear_tier("L2")

            if self.state == AgentState.ANSWER:
                answer = self.context.get("answer", "Task completed")
                self._log_event("agent.answer", {"answer": answer})
                if self.telemetry:
                    self.telemetry.log_agent_answer(answer)
                if self.metrics:
                    self.metrics.record_agent_task("success")

                return {
                    "ok": True,
                    "answer": answer,
                    "iterations": self.iteration,
                    "tool_calls": self.tool_calls,
                    "elapsed_ms": elapsed_ms,
                }
            else:
                error = self.context.get("error", "Agent aborted")
                self._log_event("agent.error", {"error": error})
                if self.metrics:
                    self.metrics.record_agent_task("error")

                return {
                    "ok": False,
                    "error": error,
                    "iterations": self.iteration,
                    "tool_calls": self.tool_calls,
                    "elapsed_ms": elapsed_ms,
                }

        except Exception as e:
            elapsed_ms = int((time.perf_counter() * 1000) - self.start_time_ms)
            error = f"Agent loop crashed: {e}"
            self._log_event("agent.exception", {"error": error})

            # Clear loop memory even on exception
            self.memory.clear_tier("L2")
            if self.metrics:
                self.metrics.record_agent_task("exception")

            return {
                "ok": False,
                "error": error,
                "iterations": self.iteration,
                "tool_calls": self.tool_calls,
                "elapsed_ms": elapsed_ms,
            }

    def _execute_plan(self, task: str) -> None:
        """Execute PLAN state: call LLM to decide next action."""
        self._log_event("agent.plan", {"iteration": self.iteration})
        if self.telemetry:
            self.telemetry.log_agent_plan(self.iteration)

        prompt = self._build_prompt(task)
        llm_response = self.llm(prompt)

        self._log_event("agent.llm_response", {"response": llm_response})

        # Parse response
        action = self._parse_llm_response(llm_response)
        self.context["next_action"] = action

        # Transition based on action
        if action["action"] == "call_tool":
            self._transition(AgentState.CALL_TOOL)
        elif action["action"] == "answer":
            self.context["answer"] = action["answer"]
            self._transition(AgentState.ANSWER)
        elif action["action"] == "refine":
            self.context["question"] = action["question"]
            self._transition(AgentState.REFINE)
        else:
            self.context["error"] = f"Unknown action: {action['action']}"
            self._transition(AgentState.ABORT)

    def _execute_tool(self) -> None:
        """Execute CALL_TOOL state: invoke tool with token."""
        action = self.context.get("next_action", {})
        tool_name = action.get("tool")
        args = action.get("args", {})

        self._log_event("tool.call", {"tool": tool_name, "args": args})
        if self.telemetry:
            self.telemetry.log_tool_call(tool_name, args)

        # Track start time for metrics
        start_time = time.perf_counter()

        # Call tool with auto-token generation
        result = self.tools.call_with_auto_token(
            name=tool_name,
            args=args,
            ttl_s=30,
            budget_ms=5000,
        )

        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        self.tool_calls += 1
        self._log_event("tool.result", {"tool": tool_name, **result})

        # Log to telemetry
        if self.telemetry:
            self.telemetry.log_tool_result(
                tool=tool_name,
                ok=result.get("ok", False),
                result=result.get("result"),
                error=result.get("error"),
                latency_ms=latency_ms,
            )
        if self.metrics:
            self.metrics.record_tool_call(
                tool_name=tool_name,
                latency_ms=latency_ms,
                success=result.get("ok", False),
            )

        # Store result in context and loop memory (L2)
        self.context["last_tool_result"] = result
        self.memory.write(f"tool.{tool_name}.last_result", result, tier="L2")
        self.memory.write("last_tool_name", tool_name, tier="L2")

        # Transition to OBSERVE
        self._transition(AgentState.OBSERVE)

    def _execute_observe(self) -> None:
        """Execute OBSERVE state: process tool result and decide next."""
        result = self.context.get("last_tool_result", {})

        if not result.get("ok"):
            # Tool failed - log and abort
            error = result.get("error", "Unknown tool error")
            self._log_event("agent.tool_failed", {"error": error})
            self.context["error"] = error
            self._transition(AgentState.ABORT)
        else:
            # Tool succeeded - go back to planning
            self._transition(AgentState.PLAN)

    def _execute_refine(self) -> None:
        """Execute REFINE state: ask clarifying question (currently unsupported)."""
        question = self.context.get("question", "Need more information")
        self._log_event("agent.refine", {"question": question})

        # For now, treat REFINE as abort (interactive mode not implemented)
        self.context["error"] = f"Clarification needed: {question}"
        self._transition(AgentState.ABORT)


def create_agent(
    tool_registry: ToolRegistry | None = None,
    llm_func: Callable[[str], str] | None = None,
) -> AgentKernel:
    """
    Create a default agent kernel instance.

    Args:
        tool_registry: Optional tool registry (creates default if None)
        llm_func: Optional LLM function (uses mock if None)

    Returns:
        Configured AgentKernel instance
    """
    from agent_kernel.tools import create_default_registry

    if tool_registry is None:
        tool_registry = create_default_registry()

    return AgentKernel(
        tool_registry=tool_registry,
        llm_func=llm_func,
        max_iterations=10,
        max_tool_calls=20,
        loop_timeout_ms=180000,
    )
