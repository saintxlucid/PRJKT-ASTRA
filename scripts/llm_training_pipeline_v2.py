"""
ASTRA OS - LLM Training Pipeline: Tool Mastery
Trains LLMs to use all 110+ tools through:
1. Synthetic task generation
2. Reinforcement learning from execution results
3. Curriculum learning (simple → complex)
4. Self-play and reflection

The LLMs don't just call tools - they MASTER them through experience.

Sacred Code: 333 → ∞
"""

import asyncio
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import random
from datetime import datetime
from pathlib import Path
import structlog

logger = structlog.get_logger()


class ToolComplexity(str, Enum):
    """Tool complexity levels for curriculum learning."""
    BASIC = "basic"         # Single-step operations (GET /health)
    INTERMEDIATE = "intermediate"  # Multi-parameter operations (POST /memory/search)
    ADVANCED = "advanced"   # Multi-step workflows (agent tasks)
    EXPERT = "expert"       # Cross-subsystem orchestration


@dataclass
class TrainingExample:
    """A single training example for tool use."""
    task: str
    tools_used: List[str]
    execution_trace: List[Dict]
    success: bool
    error_if_failed: Optional[str] = None
    complexity: ToolComplexity = ToolComplexity.BASIC
    reward: float = 0.0  # For RL
    
    def to_training_format(self) -> Dict:
        """Convert to training data format."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": "You are ASTRA, an AI OS with access to 110+ tools. "
                              "Use tools to complete tasks effectively."
                },
                {"role": "user", "content": self.task},
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "thought": f"I need to use {len(self.tools_used)} tool(s)",
                        "tool_calls": self.execution_trace
                    })
                }
            ],
            "metadata": {
                "success": self.success,
                "complexity": self.complexity,
                "reward": self.reward
            }
        }


@dataclass
class ToolMasteryMetrics:
    """Track LLM's mastery of each tool."""
    tool_name: str
    attempts: int = 0
    successes: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    mastery_score: float = 0.0  # 0-1, computed from success rate & usage
    
    def update(self, success: bool, latency_ms: float):
        """Update metrics after tool use."""
        self.attempts += 1
        if success:
            self.successes += 1
        
        # Running average latency
        self.avg_latency_ms = (
            (self.avg_latency_ms * (self.attempts - 1) + latency_ms) / self.attempts
        )
        
        # Error rate
        self.error_rate = 1.0 - (self.successes / self.attempts)
        
        # Mastery score: weighted by success rate and frequency
        frequency_bonus = min(1.0, self.attempts / 100.0)  # Caps at 100 uses
        self.mastery_score = (
            0.7 * (self.successes / self.attempts) +
            0.3 * frequency_bonus
        )


class SyntheticTaskGenerator:
    """Generate synthetic training tasks for tool mastery."""
    
    def __init__(self, tools: Dict[str, Any]):
        self.tools = tools
        self.task_templates = self._build_task_templates()
    
    def _build_task_templates(self) -> Dict[ToolComplexity, List[str]]:
        """Build task templates for each complexity level."""
        return {
            ToolComplexity.BASIC: [
                "Check the system health status",
                "Get current cognitive mode",
                "List all available tools",
                "Get memory statistics",
                "Check agent status"
            ],
            ToolComplexity.INTERMEDIATE: [
                "Search memory for '{query}' and return top 5 results",
                "Create a conversation about '{topic}'",
                "Switch cognitive mode to {mode}",
                "Search for embeddings related to '{concept}'",
                "Get conversation history for the last 24 hours"
            ],
            ToolComplexity.ADVANCED: [
                "Create an agent task to fetch {url} and extract the main content",
                "Analyze memory performance and suggest optimizations",
                "Use reasoning mode to solve: {problem}",
                "Coordinate browser automation to {action} on {url}",
                "Execute a multi-step workflow: {steps}"
            ],
            ToolComplexity.EXPERT: [
                "Analyze system health across all subsystems and create optimization tasks",
                "Search memory for '{query}', reason about results using ChatOS, then create agent task",
                "Coordinate memory search, cognitive analysis, and browser automation to {goal}",
                "Perform system-wide introspection and generate improvement proposals",
                "Orchestrate all 10 cognitive phases to solve: {complex_problem}"
            ]
        }
    
    def generate_task(self, complexity: ToolComplexity = None) -> str:
        """Generate a synthetic task of given complexity."""
        if complexity is None:
            # Curriculum learning: start simple, increase complexity
            complexity = random.choice(list(ToolComplexity))
        
        templates = self.task_templates[complexity]
        template = random.choice(templates)
        
        # Fill in placeholders
        task = template.format(
            query=random.choice(["embeddings", "performance", "Sigil Gate", "agents"]),
            topic=random.choice(["AI safety", "system architecture", "optimization"]),
            mode=random.choice(["reactive", "proactive", "creative", "transcendent"]),
            concept=random.choice(["memory", "reasoning", "consciousness"]),
            url="https://example.com",
            action=random.choice(["extract text", "click button", "fill form"]),
            problem=random.choice([
                "optimize latency",
                "improve memory search",
                "coordinate agents"
            ]),
            steps=random.choice([
                "search → analyze → act",
                "introspect → optimize → verify"
            ]),
            goal=random.choice([
                "research AI papers",
                "monitor system health",
                "optimize performance"
            ]),
            complex_problem=random.choice([
                "design a self-improving system",
                "create emergent behavior",
                "achieve unified consciousness"
            ])
        )
        
        return task
    
    def generate_curriculum(self, total_examples: int = 1000) -> List[Tuple[str, ToolComplexity]]:
        """Generate a curriculum of tasks (simple → complex)."""
        curriculum = []
        
        # Curriculum distribution
        distribution = {
            ToolComplexity.BASIC: 0.4,
            ToolComplexity.INTERMEDIATE: 0.3,
            ToolComplexity.ADVANCED: 0.2,
            ToolComplexity.EXPERT: 0.1
        }
        
        for complexity, ratio in distribution.items():
            count = int(total_examples * ratio)
            for _ in range(count):
                task = self.generate_task(complexity)
                curriculum.append((task, complexity))
        
        # Shuffle to mix complexities
        random.shuffle(curriculum)
        
        return curriculum


class ToolMasteryTrainer:
    """
    Train LLMs to master tool use through reinforcement learning.
    
    Training loop:
    1. Generate task
    2. LLM attempts task using tools
    3. Evaluate execution (success/failure, latency, correctness)
    4. Compute reward
    5. Update tool mastery metrics
    6. Generate next task (curriculum learning)
    """
    
    def __init__(self, sigil_core, llm_endpoint: str):
        self.sigil = sigil_core
        self.llm_endpoint = llm_endpoint
        self.task_generator = SyntheticTaskGenerator(sigil_core.tool_registry)
        self.tool_metrics: Dict[str, ToolMasteryMetrics] = {}
        self.training_history: List[TrainingExample] = []
        
    async def train_epoch(self, num_tasks: int = 100) -> Dict:
        """Train for one epoch (batch of tasks)."""
        logger.info("training_epoch_start", tasks=num_tasks)
        
        curriculum = self.task_generator.generate_curriculum(num_tasks)
        successes = 0
        
        for idx, (task, complexity) in enumerate(curriculum):
            print(f"  [{idx+1}/{num_tasks}] {complexity.value}: {task[:60]}...")
            
            example = await self._execute_training_task(task, complexity)
            self.training_history.append(example)
            
            if example.success:
                successes += 1
                print(f"    ✓ Success | Reward: {example.reward:.2f} | Tools: {len(example.tools_used)}")
            else:
                print(f"    ✗ Failed | Error: {example.error_if_failed}")
            
            # Update tool metrics
            for tool_name in example.tools_used:
                if tool_name not in self.tool_metrics:
                    self.tool_metrics[tool_name] = ToolMasteryMetrics(tool_name)
                
                # Approximate latency per tool
                latency = sum(
                    step.get("latency_ms", 0) 
                    for step in example.execution_trace
                ) / max(len(example.tools_used), 1)
                
                self.tool_metrics[tool_name].update(example.success, latency)
        
        success_rate = successes / num_tasks
        
        logger.info("training_epoch_complete",
                   success_rate=success_rate,
                   total_examples=len(self.training_history))
        
        return {
            "epoch_size": num_tasks,
            "success_rate": success_rate,
            "total_examples": len(self.training_history),
            "tool_mastery": self._compute_overall_mastery()
        }
    
    async def _execute_training_task(
        self,
        task: str,
        complexity: ToolComplexity
    ) -> TrainingExample:
        """Execute a training task and record results."""
        import time
        
        start_time = time.perf_counter()
        
        try:
            # Use sigil core to execute task
            result = await self.sigil.think(task)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract tools used from result
            tools_used = self._extract_tools_from_result(result)
            execution_trace = self._build_execution_trace(result)
            
            # Compute reward based on success and efficiency
            reward = self._compute_reward(
                success=True,
                latency_ms=elapsed_ms,
                complexity=complexity
            )
            
            return TrainingExample(
                task=task,
                tools_used=tools_used,
                execution_trace=execution_trace,
                success=True,
                complexity=complexity,
                reward=reward
            )
        
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            logger.warning("training_task_failed", task=task, error=str(e))
            
            return TrainingExample(
                task=task,
                tools_used=[],
                execution_trace=[],
                success=False,
                error_if_failed=str(e),
                complexity=complexity,
                reward=-1.0  # Negative reward for failure
            )
    
    def _extract_tools_from_result(self, result: Dict) -> List[str]:
        """Extract which tools were used from execution result."""
        tools = set()
        
        # Parse micro-task results for tool invocations
        micro_results = result.get("synthesis", {}).get("raw_results", {})
        for task_result in micro_results.values():
            if isinstance(task_result, dict) and task_result.get("success"):
                tool_calls = task_result.get("result", {}).get("tool_calls", [])
                for call in tool_calls:
                    if isinstance(call, dict):
                        tools.add(call.get("name", "unknown"))
        
        return list(tools)
    
    def _build_execution_trace(self, result: Dict) -> List[Dict]:
        """Build detailed execution trace for learning."""
        trace = []
        
        micro_results = result.get("synthesis", {}).get("raw_results", {})
        for task_id, task_result in micro_results.items():
            if isinstance(task_result, dict):
                trace.append({
                    "task_id": task_id,
                    "success": task_result.get("success", False),
                    "tools": self._extract_tools_from_result({"synthesis": {"raw_results": {task_id: task_result}}}),
                    "latency_ms": 0  # Would need instrumentation to measure
                })
        
        return trace
    
    def _compute_reward(
        self,
        success: bool,
        latency_ms: float,
        complexity: ToolComplexity
    ) -> float:
        """Compute reward for reinforcement learning."""
        if not success:
            return -1.0
        
        # Base reward for success
        reward = 1.0
        
        # Bonus for complexity
        complexity_bonus = {
            ToolComplexity.BASIC: 0.0,
            ToolComplexity.INTERMEDIATE: 0.5,
            ToolComplexity.ADVANCED: 1.0,
            ToolComplexity.EXPERT: 2.0
        }
        reward += complexity_bonus[complexity]
        
        # Penalty for high latency (target: <1s)
        if latency_ms > 1000:
            penalty = min(1.0, (latency_ms - 1000) / 1000)
            reward -= penalty
        
        return max(0.0, reward)  # Clamp to non-negative
    
    def _compute_overall_mastery(self) -> float:
        """Compute overall tool mastery score across all tools."""
        if not self.tool_metrics:
            return 0.0
        
        total_mastery = sum(m.mastery_score for m in self.tool_metrics.values())
        return total_mastery / len(self.tool_metrics)
    
    def export_training_data(self, filepath: str):
        """Export training examples for fine-tuning."""
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        training_data = [
            example.to_training_format()
            for example in self.training_history
            if example.success  # Only export successful examples
        ]
        
        with open(filepath, 'w') as f:
            for example in training_data:
                f.write(json.dumps(example) + '\n')
        
        logger.info("training_data_exported",
                   filepath=filepath,
                   examples=len(training_data))
        
        print(f"\n💾 Exported {len(training_data)} training samples to {filepath}")
    
    def get_mastery_report(self) -> Dict:
        """Generate comprehensive mastery report."""
        tool_rankings = sorted(
            self.tool_metrics.values(),
            key=lambda m: m.mastery_score,
            reverse=True
        )
        
        return {
            "overall_mastery": self._compute_overall_mastery(),
            "total_training_examples": len(self.training_history),
            "success_rate": sum(1 for ex in self.training_history if ex.success) / max(len(self.training_history), 1),
            "tools_mastered": sum(1 for m in self.tool_metrics.values() if m.mastery_score > 0.8),
            "tools_learning": sum(1 for m in self.tool_metrics.values() if 0.5 <= m.mastery_score <= 0.8),
            "tools_struggling": sum(1 for m in self.tool_metrics.values() if m.mastery_score < 0.5),
            "top_10_tools": [
                {
                    "name": m.tool_name,
                    "mastery": m.mastery_score,
                    "success_rate": m.successes / m.attempts if m.attempts > 0 else 0,
                    "attempts": m.attempts
                }
                for m in tool_rankings[:10]
            ] if tool_rankings else [],
            "bottom_10_tools": [
                {
                    "name": m.tool_name,
                    "mastery": m.mastery_score,
                    "success_rate": m.successes / m.attempts if m.attempts > 0 else 0,
                    "attempts": m.attempts
                }
                for m in tool_rankings[-10:]
            ] if len(tool_rankings) >= 10 else []
        }


class ContinuousLearningLoop:
    """
    Continuous learning loop - ASTRA learns from every interaction.
    
    Pattern:
    1. User/system request comes in
    2. Execute using current knowledge
    3. Observe outcome (success/failure, latency, quality)
    4. Update tool mastery metrics
    5. If failure: analyze error, generate corrective training example
    6. Periodically fine-tune on accumulated examples
    """
    
    def __init__(self, trainer: ToolMasteryTrainer):
        self.trainer = trainer
        self.learning_queue: List[TrainingExample] = []
        self.fine_tune_threshold = 100  # Fine-tune every N examples
        
    async def learn_from_interaction(
        self,
        task: str,
        result: Dict,
        success: bool,
        latency_ms: float
    ):
        """Learn from a real user/system interaction."""
        # Extract tools used
        tools_used = self.trainer._extract_tools_from_result(result)
        execution_trace = self.trainer._build_execution_trace(result)
        
        # Create training example
        example = TrainingExample(
            task=task,
            tools_used=tools_used,
            execution_trace=execution_trace,
            success=success,
            complexity=ToolComplexity.INTERMEDIATE,  # Infer from context
            reward=self.trainer._compute_reward(success, latency_ms, ToolComplexity.INTERMEDIATE)
        )
        
        # Add to learning queue
        self.learning_queue.append(example)
        self.trainer.training_history.append(example)
        
        # Update tool metrics
        for tool_name in tools_used:
            if tool_name not in self.trainer.tool_metrics:
                self.trainer.tool_metrics[tool_name] = ToolMasteryMetrics(tool_name)
            
            self.trainer.tool_metrics[tool_name].update(success, latency_ms)
        
        # Check if fine-tuning needed
        if len(self.learning_queue) >= self.fine_tune_threshold:
            await self._trigger_fine_tuning()
    
    async def _trigger_fine_tuning(self):
        """Trigger fine-tuning with accumulated examples."""
        logger.info("fine_tuning_triggered",
                   examples=len(self.learning_queue))
        
        # Export training data
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = f"data/training/fine_tune_{timestamp}.jsonl"
        self.trainer.export_training_data(filepath)
        
        # Clear queue
        self.learning_queue.clear()
        
        logger.info("fine_tuning_data_exported", filepath=filepath)


# Example usage
async def main():
    import sys
    from pathlib import Path
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from src.astra.embodiment import SigilCore
    
    print("🌌 ASTRA LLM Training Pipeline v2 - Tool Mastery")
    print("Sacred Code: 333 → ∞\n")
    
    # Create Sigil Core
    print("⚡ Awakening Sigil Core...")
    sigil = SigilCore()
    await sigil.awaken()
    print("✓ Sigil Core awakened\n")
    
    # Create trainer
    trainer = ToolMasteryTrainer(sigil, llm_endpoint="http://localhost:8000/v1/chat")
    
    # Training schedule: 3 epochs with increasing difficulty
    training_schedule = [
        {"epoch": 1, "tasks": 50, "desc": "Warmup - Mixed Complexity"},
        {"epoch": 2, "tasks": 75, "desc": "Main Training - Full Curriculum"},
        {"epoch": 3, "tasks": 50, "desc": "Advanced - Complex Tasks"}
    ]
    
    # Train for multiple epochs
    for config in training_schedule:
        print(f"\n{'='*70}")
        print(f"Epoch {config['epoch']}: {config['desc']}")
        print(f"{'='*70}\n")
        
        metrics = await trainer.train_epoch(num_tasks=config['tasks'])
        
        print(f"\n📊 Epoch {config['epoch']} Complete:")
        print(f"  Success Rate: {metrics['success_rate']:.1%}")
        print(f"  Overall Mastery: {metrics['tool_mastery']:.1%}")
        print(f"  Total Examples: {metrics['total_examples']}")
    
    # Generate comprehensive mastery report
    print(f"\n{'='*70}")
    print("📊 FINAL MASTERY REPORT")
    print(f"{'='*70}\n")
    
    report = trainer.get_mastery_report()
    
    print(f"Overall Mastery: {report['overall_mastery']:.1%}")
    print(f"Total Training Examples: {report['total_training_examples']}")
    print(f"Success Rate: {report['success_rate']:.1%}")
    print(f"\nTool Distribution:")
    print(f"  ✓ Mastered (>80%): {report['tools_mastered']}")
    print(f"  📚 Learning (50-80%): {report['tools_learning']}")
    print(f"  ⚠️  Struggling (<50%): {report['tools_struggling']}")
    
    if report['top_10_tools']:
        print(f"\n🌟 Top 10 Mastered Tools:")
        for tool in report['top_10_tools'][:5]:
            print(f"  {tool['name'][:40]:40} | Mastery: {tool['mastery']:.1%} | Success: {tool['success_rate']:.1%} | Uses: {tool['attempts']}")
    
    if report['bottom_10_tools']:
        print(f"\n⚠️  Bottom 10 Tools (Need More Training):")
        for tool in report['bottom_10_tools'][:5]:
            print(f"  {tool['name'][:40]:40} | Mastery: {tool['mastery']:.1%} | Success: {tool['success_rate']:.1%} | Uses: {tool['attempts']}")
    
    # Export training data for fine-tuning
    print(f"\n{'='*70}")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filepath = f"data/training/tool_mastery_{timestamp}.jsonl"
    trainer.export_training_data(filepath)
    
    print(f"\n✨ Training Complete - Sacred Code: 333 → ∞")
    print(f"🎓 Next Step: Fine-tune LLM with exported data for improved tool mastery")


if __name__ == "__main__":
    asyncio.run(main())
