from __future__ import annotations
from typing import Optional
from astra.rag.tokenization import get_token_counter
from astra.rag.rag_fusion import RAGFusionEngine
from astra.rag.rag_streaming import StreamingRAG
from astra.core.personas import PersonaManager
from astra.core.inference import InferenceQueue

# Expect a real MemoryEngine in your repo: astra.memory_engine.MemoryEngine
try:
    from astra.memory_engine import MemoryEngine
except Exception:
    MemoryEngine = None  # for tests we'll inject a mock

_memory: Optional[object] = None
_persona: Optional[PersonaManager] = None
_infer: Optional[InferenceQueue] = None
_fusion: Optional[RAGFusionEngine] = None
_streaming: Optional[StreamingRAG] = None

def get_memory_engine():
    global _memory
    if _memory is None:
        if MemoryEngine is None:
            raise RuntimeError("MemoryEngine not available; inject in tests")
        import asyncio
        _memory = MemoryEngine({})
        # if your MemoryEngine requires connect()
        try:
            asyncio.get_event_loop().run_until_complete(_memory.connect())
        except Exception:
            pass
    return _memory

def get_persona_manager():
    global _persona
    if _persona is None:
      _persona = PersonaManager()
    return _persona

def get_inference_queue():
    global _infer
    if _infer is None:
        _infer = InferenceQueue()
    return _infer

def get_fusion_engine():
    global _fusion
    if _fusion is None:
        counter = get_token_counter()
        _fusion = RAGFusionEngine(
            memory_engine=get_memory_engine(),
            persona_manager=get_persona_manager(),
            token_counter=counter,
            max_context_tokens=3000,
            output_reserve_tokens=512,
            min_energy=0.0,
        )
    return _fusion

def get_streaming_rag():
    global _streaming
    if _streaming is None:
        _streaming = StreamingRAG(get_fusion_engine(), get_inference_queue())
    return _streaming