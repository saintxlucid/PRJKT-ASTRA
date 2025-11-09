"""
Mock implementations for testing
Created: October 31, 2025
"""
import random
import asyncio
from typing import Dict, Any

class MockInference:
    """Mock inference provider for testing"""
    
    async def complete(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """Return mock completion"""
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate latency
        return {
            "text": f"Mock answer to '{query}' with context: {context}",
            "metadata": {"test": True}
        }

class MockRAGFusionEngine:
    """Mock RAG fusion engine for testing"""
    
    async def fuse(self, query: str, **kwargs) -> dict:
        """Return mock fusion result"""
        return {
            "context": f"Mock context for query: {query}",
            "citations": [],
            "metadata": {"test": True}
        }