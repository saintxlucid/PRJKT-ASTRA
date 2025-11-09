"""
ASTRA Dependency Injection
Created: October 25, 2025

FastAPI dependency providers for core ASTRA components.
"""
from typing import Generator
from fastapi import Depends

from astra.core.rag_fusion import RAGFusionEngine
from astra.core.personas import PersonaManager
from astra.core.inference import InferenceQueue
from astra.core.memory import MemoryEngine

def get_memory_engine() -> MemoryEngine:
    """Provides singleton MemoryEngine"""
    return MemoryEngine()
    
def get_inference_queue() -> InferenceQueue:
    """Provides singleton InferenceQueue"""
    return InferenceQueue()
    
def get_persona_manager() -> PersonaManager:
    """Provides singleton PersonaManager"""
    return PersonaManager()
    
def get_rag_engine(
    memory_engine: MemoryEngine = Depends(get_memory_engine),
    persona_manager: PersonaManager = Depends(get_persona_manager),
    inference_queue: InferenceQueue = Depends(get_inference_queue)
) -> Generator[RAGFusionEngine, None, None]:
    """Provides RAG engine with dependencies"""
    engine = RAGFusionEngine(
        memory_engine=memory_engine,
        persona_manager=persona_manager,
        inference_queue=inference_queue
    )
    try:
        yield engine
    finally:
        # Cleanup if needed
        pass