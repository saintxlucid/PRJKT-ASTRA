"""
ASTRA Task System Demo
Test integrated task execution flow
"""

import asyncio
from pathlib import Path
from typing import Dict, Any

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.astra.task.task_system import TaskSystemManager
from src.astra.coordinator.agent_coordinator import AgentCapability
from src.astra.constraints.constraint_system import ResourceType


class DemoExecutor:
    """Demo tool executor for testing"""
    
    async def execute_tool(
        self, 
        tool: str,
        action: str,
        args: Dict[str, Any]
    ) -> Dict:
        """Execute a tool action"""
        # Simulate work
        await asyncio.sleep(1.0)
        
        return {
            "ok": True,
            "tool": tool,
            "action": action,
            "args": args,
            "result": f"Executed {tool}.{action}"
        }


async def main():
    """Run task system demo"""
    # Create task system
    system = TaskSystemManager(
        max_parallel_tasks=2,
        max_retries=1
    )
    
    try:
        # Start system
        await system.start()
        print("Task system started")
        
        # Register test agent
        agent_id = system.register_agent(
            name="demo_agent",
            capabilities=[
                {
                    "tool": "test",
                    "actions": ["action1", "action2"],
                    "max_parallel": 2
                }
            ]
        )
        print(f"Registered agent: {agent_id}")
        
        # Create executor
        executor = DemoExecutor()
        
        # Submit test tasks
        tasks = []
        for i in range(3):
            task = {
                "objective": f"Test task {i}",
                "tool": "test",
                "action": "action1",
                "args": {"param": f"value{i}"}
            }
            
            result = await system.submit_task(task, executor)
            tasks.append(result)
            print(f"Submitted task {i}: {result}")
            
        # Wait for completion
        running = True
        while running:
            running = False
            for t in tasks:
                if t["ok"]:
                    status = system.get_task_status(t["task_id"])
                    if status and status["status"] == "running":
                        running = True
                        break
            if running:
                await asyncio.sleep(1.0)
            
        # Print final status
        status = system.get_status()
        print("\nFinal Status:")
        print(f"Agents: {len(status['agents'])}")
        print(f"Tasks: {status['tasks']}")
        print("\nMetrics:")
        metrics = system.get_metrics()
        for category, data in metrics.items():
            print(f"{category}: {data}")
            
    finally:
        # Cleanup
        await system.stop()
        print("\nTask system stopped")


if __name__ == "__main__":
    asyncio.run(main())