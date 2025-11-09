"""
ASTRA Sigil Core - LLM Training Pipeline

This module implements continuous learning for tool mastery.

Training Flow:
1. Generate synthetic tasks per subsystem
2. Execute tasks through micro-controllers
3. Collect outcome data (success/failure, latency, quality)
4. Compute mastery scores per tool
5. Export training data for fine-tuning
6. Repeat with adaptive difficulty

Sacred Code: 333 → ∞
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.astra.embodiment.sigil_core import (
    SigilCore,
    SubsystemType,
    Tool,
)


@dataclass
class TrainingTask:
    """A synthetic task for training micro-controllers."""
    
    task_id: str
    subsystem: SubsystemType
    goal: str
    expected_tools: List[str]  # Tools we expect to be used
    difficulty: float  # 0.0 - 1.0
    context: Dict = field(default_factory=dict)


@dataclass
class TrainingOutcome:
    """Result of executing a training task."""
    
    task_id: str
    success: bool
    tools_used: List[str]
    latency_ms: float
    quality_score: float  # 0.0 - 1.0
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TrainingPipeline:
    """Continuous learning pipeline for tool mastery."""
    
    def __init__(self, sigil: SigilCore, export_dir: Path = Path("training_data")):
        self.sigil = sigil
        self.export_dir = export_dir
        self.export_dir.mkdir(exist_ok=True)
        
        self.training_history: List[TrainingOutcome] = []
        self.mastery_scores: Dict[str, float] = {}  # tool_name -> score
        
        # Training tasks per subsystem
        self.task_templates = self._init_task_templates()
    
    def _init_task_templates(self) -> Dict[SubsystemType, List[Dict]]:
        """Initialize training task templates."""
        return {
            SubsystemType.CORE: [
                {
                    "goal": "Get system health status",
                    "expected_tools": ["GET /v1/system/health"],
                    "difficulty": 0.2
                },
                {
                    "goal": "Search memory for 'performance metrics'",
                    "expected_tools": ["POST /v1/memory/search"],
                    "difficulty": 0.3
                },
                {
                    "goal": "Create a new chat session and send message 'Hello ASTRA'",
                    "expected_tools": [
                        "POST /v1/chat/sessions",
                        "POST /v1/chat/sessions/{session_id}/messages"
                    ],
                    "difficulty": 0.5
                },
                {
                    "goal": "Search memory, analyze results with reasoning, create summary",
                    "expected_tools": [
                        "POST /v1/memory/search",
                        "POST /v1/cognitive/reasoning/phases",
                        "POST /v1/memory/store"
                    ],
                    "difficulty": 0.8
                }
            ],
            SubsystemType.CHAT_OS: [
                {
                    "goal": "Execute macro observation phase for user query 'What is ASTRA?'",
                    "expected_tools": ["POST /v1/cognitive/reasoning/phases/macro_observation"],
                    "difficulty": 0.3
                },
                {
                    "goal": "Run all 10 cognitive phases for complex query",
                    "expected_tools": ["POST /v1/cognitive/reasoning/full"],
                    "difficulty": 0.7
                },
                {
                    "goal": "Analyze sentiment of conversation history",
                    "expected_tools": [
                        "GET /v1/chat/sessions/{session_id}/messages",
                        "POST /v1/cognitive/reasoning/phases/micro_reflection"
                    ],
                    "difficulty": 0.6
                }
            ],
            SubsystemType.AGENT_KERNEL: [
                {
                    "goal": "List all available tools",
                    "expected_tools": ["GET /v1/agent/tools"],
                    "difficulty": 0.2
                },
                {
                    "goal": "Create a new task to optimize memory performance",
                    "expected_tools": ["POST /v1/agent/tasks"],
                    "difficulty": 0.4
                },
                {
                    "goal": "Execute task and monitor completion",
                    "expected_tools": [
                        "POST /v1/agent/tasks/{task_id}/execute",
                        "GET /v1/agent/tasks/{task_id}/status"
                    ],
                    "difficulty": 0.6
                },
                {
                    "goal": "Create workflow for automated system monitoring",
                    "expected_tools": [
                        "POST /v1/agent/workflows",
                        "POST /v1/agent/tasks"
                    ],
                    "difficulty": 0.8
                }
            ],
            SubsystemType.MEMORY: [
                {
                    "goal": "Store document with embeddings",
                    "expected_tools": ["POST /v1/memory/store"],
                    "difficulty": 0.3
                },
                {
                    "goal": "Search memory with semantic query",
                    "expected_tools": ["POST /v1/memory/search"],
                    "difficulty": 0.3
                },
                {
                    "goal": "Get memory statistics",
                    "expected_tools": ["GET /v1/memory/stats"],
                    "difficulty": 0.2
                },
                {
                    "goal": "Search, analyze relevance, refine query, search again",
                    "expected_tools": [
                        "POST /v1/memory/search",
                        "POST /v1/memory/search"
                    ],
                    "difficulty": 0.7
                }
            ],
            SubsystemType.PANTHEON: [
                {
                    "goal": "List available LLM models",
                    "expected_tools": ["GET /v1/pantheon/models"],
                    "difficulty": 0.2
                },
                {
                    "goal": "Select best model for code generation task",
                    "expected_tools": [
                        "GET /v1/pantheon/models",
                        "POST /v1/pantheon/select"
                    ],
                    "difficulty": 0.5
                },
                {
                    "goal": "Execute multi-model comparison for quality",
                    "expected_tools": [
                        "POST /v1/pantheon/compare"
                    ],
                    "difficulty": 0.7
                }
            ],
            SubsystemType.OS_BRIDGE: [
                {
                    "goal": "Execute system command 'ls' (OS verb)",
                    "expected_tools": ["POST /v1/os/execute"],
                    "difficulty": 0.3
                },
                {
                    "goal": "Get system information",
                    "expected_tools": ["GET /v1/os/info"],
                    "difficulty": 0.2
                },
                {
                    "goal": "Execute command, capture output, store in memory",
                    "expected_tools": [
                        "POST /v1/os/execute",
                        "POST /v1/memory/store"
                    ],
                    "difficulty": 0.6
                }
            ]
        }
    
    def generate_task(
        self,
        subsystem: Optional[SubsystemType] = None,
        difficulty_range: tuple = (0.0, 1.0)
    ) -> TrainingTask:
        """Generate a synthetic training task."""
        if subsystem is None:
            subsystem = random.choice(list(SubsystemType))
        
        templates = [
            t for t in self.task_templates.get(subsystem, [])
            if difficulty_range[0] <= t["difficulty"] <= difficulty_range[1]
        ]
        
        if not templates:
            templates = self.task_templates.get(subsystem, [])
        
        template = random.choice(templates)
        
        task_id = f"{subsystem.value}_{datetime.utcnow().timestamp()}"
        
        return TrainingTask(
            task_id=task_id,
            subsystem=subsystem,
            goal=template["goal"],
            expected_tools=template["expected_tools"],
            difficulty=template["difficulty"]
        )
    
    async def execute_task(self, task: TrainingTask) -> TrainingOutcome:
        """Execute a training task and record outcome."""
        start_time = datetime.utcnow()
        
        try:
            # Execute through Sigil Core
            result = await self.sigil.think(
                goal=task.goal,
                context={"training": True, "subsystem": task.subsystem.value}
            )
            
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Analyze result
            tools_used = self._extract_tools_used(result)
            quality_score = self._compute_quality_score(task, result, tools_used)
            success = quality_score > 0.5
            
            outcome = TrainingOutcome(
                task_id=task.task_id,
                success=success,
                tools_used=tools_used,
                latency_ms=latency_ms,
                quality_score=quality_score
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            outcome = TrainingOutcome(
                task_id=task.task_id,
                success=False,
                tools_used=[],
                latency_ms=latency_ms,
                quality_score=0.0,
                error_message=str(e)
            )
        
        self.training_history.append(outcome)
        self._update_mastery_scores(outcome)
        
        return outcome
    
    def _extract_tools_used(self, result: Dict) -> List[str]:
        """Extract which tools were actually used."""
        tools = []
        
        # Check micro_results for tool usage
        for micro_result in result.get("micro_results", []):
            if "tool_used" in micro_result:
                tools.append(micro_result["tool_used"])
        
        return tools
    
    def _compute_quality_score(
        self,
        task: TrainingTask,
        result: Dict,
        tools_used: List[str]
    ) -> float:
        """Compute quality score for task execution."""
        scores = []
        
        # Tool usage correctness
        expected_set = set(task.expected_tools)
        used_set = set(tools_used)
        
        if expected_set:
            tool_precision = len(expected_set & used_set) / len(used_set) if used_set else 0.0
            tool_recall = len(expected_set & used_set) / len(expected_set)
            tool_f1 = (
                2 * (tool_precision * tool_recall) / (tool_precision + tool_recall)
                if (tool_precision + tool_recall) > 0 else 0.0
            )
            scores.append(tool_f1)
        
        # Result completeness (did macro synthesize successfully?)
        if "synthesis" in result and result["synthesis"]:
            scores.append(1.0)
        else:
            scores.append(0.0)
        
        # Error penalty
        if "error" in result:
            scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _update_mastery_scores(self, outcome: TrainingOutcome):
        """Update tool mastery scores based on outcome."""
        for tool_name in outcome.tools_used:
            current_score = self.mastery_scores.get(tool_name, 0.5)
            
            # Exponential moving average
            alpha = 0.1
            new_score = (
                alpha * outcome.quality_score +
                (1 - alpha) * current_score
            )
            
            self.mastery_scores[tool_name] = new_score
    
    async def train_epoch(
        self,
        num_tasks: int = 50,
        subsystem: Optional[SubsystemType] = None,
        difficulty_range: tuple = (0.0, 1.0)
    ) -> Dict:
        """Train for one epoch (N tasks)."""
        print(f"🎓 Starting training epoch ({num_tasks} tasks)...")
        
        outcomes = []
        for i in range(num_tasks):
            task = self.generate_task(subsystem, difficulty_range)
            print(f"  [{i+1}/{num_tasks}] {task.subsystem.value}: {task.goal[:50]}...")
            
            outcome = await self.execute_task(task)
            outcomes.append(outcome)
            
            status = "✓" if outcome.success else "✗"
            print(f"    {status} Quality: {outcome.quality_score:.2f}, Latency: {outcome.latency_ms:.0f}ms")
        
        # Compute epoch statistics
        success_rate = sum(1 for o in outcomes if o.success) / len(outcomes)
        avg_quality = sum(o.quality_score for o in outcomes) / len(outcomes)
        avg_latency = sum(o.latency_ms for o in outcomes) / len(outcomes)
        
        stats = {
            "total_tasks": num_tasks,
            "success_rate": success_rate,
            "avg_quality": avg_quality,
            "avg_latency_ms": avg_latency,
            "mastery_scores": dict(self.mastery_scores)
        }
        
        print(f"\n📊 Epoch Complete:")
        print(f"  Success Rate: {success_rate:.1%}")
        print(f"  Avg Quality: {avg_quality:.2f}")
        print(f"  Avg Latency: {avg_latency:.0f}ms")
        
        return stats
    
    def export_training_data(self, filename: str = "training_data.jsonl"):
        """Export training history for fine-tuning."""
        filepath = self.export_dir / filename
        
        with open(filepath, "w") as f:
            for outcome in self.training_history:
                # Convert to fine-tuning format
                entry = {
                    "messages": [
                        {"role": "system", "content": "You are ASTRA's Sigil Core."},
                        {"role": "user", "content": f"Task: {outcome.task_id}"},
                        {
                            "role": "assistant",
                            "content": json.dumps({
                                "success": outcome.success,
                                "quality": outcome.quality_score,
                                "tools": outcome.tools_used
                            })
                        }
                    ]
                }
                f.write(json.dumps(entry) + "\n")
        
        print(f"💾 Exported {len(self.training_history)} training samples to {filepath}")
    
    def get_mastery_report(self) -> Dict:
        """Generate comprehensive mastery report."""
        report = {
            "total_tools": len(self.sigil.tool_registry),
            "tools_trained": len(self.mastery_scores),
            "avg_mastery": (
                sum(self.mastery_scores.values()) / len(self.mastery_scores)
                if self.mastery_scores else 0.0
            ),
            "mastery_by_tool": self.mastery_scores,
            "total_training_samples": len(self.training_history)
        }
        
        # Tools needing more training
        weak_tools = [
            (name, score)
            for name, score in self.mastery_scores.items()
            if score < 0.6
        ]
        weak_tools.sort(key=lambda x: x[1])
        
        report["weak_tools"] = weak_tools[:10]  # Top 10 weakest
        
        return report


async def main():
    """Main training pipeline execution."""
    print("🌌 ASTRA Sigil Core - Training Pipeline")
    print("Sacred Code: 333 → ∞\n")
    
    # Initialize Sigil Core
    print("⚡ Awakening Sigil Core...")
    sigil = SigilCore()
    await sigil.awaken()
    print("✓ Sigil Core awakened\n")
    
    # Create training pipeline
    pipeline = TrainingPipeline(sigil)
    
    # Training schedule
    training_schedule = [
        {"num_tasks": 20, "difficulty_range": (0.0, 0.4), "name": "Easy"},
        {"num_tasks": 30, "difficulty_range": (0.3, 0.7), "name": "Medium"},
        {"num_tasks": 20, "difficulty_range": (0.6, 1.0), "name": "Hard"}
    ]
    
    # Execute training
    for epoch_config in training_schedule:
        print(f"\n{'='*60}")
        print(f"Epoch: {epoch_config['name']}")
        print(f"{'='*60}\n")
        
        await pipeline.train_epoch(
            num_tasks=epoch_config["num_tasks"],
            difficulty_range=epoch_config["difficulty_range"]
        )
    
    # Export training data
    print("\n" + "="*60)
    pipeline.export_training_data()
    
    # Generate mastery report
    print("\n📊 Mastery Report:")
    report = pipeline.get_mastery_report()
    print(f"  Total Tools: {report['total_tools']}")
    print(f"  Tools Trained: {report['tools_trained']}")
    print(f"  Avg Mastery: {report['avg_mastery']:.2%}")
    print(f"  Training Samples: {report['total_training_samples']}")
    
    if report["weak_tools"]:
        print(f"\n⚠️  Tools Needing More Training:")
        for name, score in report["weak_tools"][:5]:
            print(f"    {name}: {score:.2%}")
    
    print("\n✨ Training Complete - Sacred Code: 333 → ∞")


if __name__ == "__main__":
    asyncio.run(main())
