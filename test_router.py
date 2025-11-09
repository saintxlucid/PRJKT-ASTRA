#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Test Multi-Model Router
========================

Quick validation of routing logic without requiring actual model servers.

Usage:
    python test_router.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.model_router import (
    ModelRouter,
    RoutingRequest,
    TaskType,
    Modality,
)


async def test_routing():
    """Test routing decisions without actual inference."""
    
    # Mock config (minimal for testing)
    config = {
        "model_router": {
            "models": {
                "deepseek_v3_1": {
                    "enabled": True,
                    "endpoint": "http://localhost:8000"
                },
                "phi_4_mini": {
                    "enabled": True,
                    "endpoint": "http://localhost:8001"
                },
                "llama_3_2_vision_11b": {
                    "enabled": True,
                    "endpoint": "http://localhost:8020"
                },
                "whisper_large_v3": {
                    "enabled": True,
                    "endpoint": "http://localhost:8004"
                }
            }
        }
    }
    
    router = ModelRouter(config)
    await router.initialize()
    
    print("🧪 Testing Multi-Model Router\n")
    
    # Test 1: Text reasoning
    print("=" * 60)
    print("Test 1: Text Reasoning Task")
    print("=" * 60)
    req = RoutingRequest(
        prompt="Explain quantum entanglement in detail",
        task_type=TaskType.REASONING,
        context_length=100
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Backend: {result.selected_model.backend.value}")
    print(f"   Reason: {result.routing_reason}")
    print(f"   Fallbacks: {[m.name for m in result.fallback_models[:2]]}")
    print(f"   Decision time: {result.decision_latency_ms:.2f}ms")
    
    # Test 2: Fast chat
    print("\n" + "=" * 60)
    print("Test 2: Fast Chat (Edge)")
    print("=" * 60)
    req = RoutingRequest(
        prompt="Hello! How are you?",
        task_type=TaskType.FAST_CHAT,
        prefer_edge=True,
        max_latency_ms=300
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Performance: {result.selected_model.max_tokens_per_sec:.1f} tok/s")
    print(f"   VRAM: {result.selected_model.min_vram_gb:.1f}GB")
    print(f"   Reason: {result.routing_reason}")
    
    # Test 3: Vision task
    print("\n" + "=" * 60)
    print("Test 3: Vision Question Answering")
    print("=" * 60)
    req = RoutingRequest(
        prompt="What objects are in this image?",
        modality=Modality.IMAGE,
        task_type=TaskType.VISION_QA,
        image_data="dummy.jpg"  # Would be actual PIL.Image
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Modalities: {[m.value for m in result.selected_model.modalities]}")
    print(f"   Context window: {result.selected_model.context_window}")
    print(f"   Reason: {result.routing_reason}")
    
    # Test 4: Tool calling
    print("\n" + "=" * 60)
    print("Test 4: Tool Calling")
    print("=" * 60)
    req = RoutingRequest(
        prompt="Search the web for latest AI news and summarize",
        task_type=TaskType.TOOL_CALLING,
        require_tool_calling=True
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Tool support: {result.selected_model.supports_tool_calling}")
    print(f"   Priority: {result.selected_model.priority}")
    print(f"   Reason: {result.routing_reason}")
    
    # Test 5: Long context
    print("\n" + "=" * 60)
    print("Test 5: Long Context (>32K tokens)")
    print("=" * 60)
    req = RoutingRequest(
        prompt="Analyze this entire codebase...",
        task_type=TaskType.LONG_CONTEXT,
        context_length=50000  # 50K tokens
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Context window: {result.selected_model.context_window:,} tokens")
    print(f"   Can handle: {'✅' if result.selected_model.context_window >= 50000 else '❌'}")
    print(f"   Reason: {result.routing_reason}")
    
    # Test 6: Audio task
    print("\n" + "=" * 60)
    print("Test 6: Audio Transcription")
    print("=" * 60)
    req = RoutingRequest(
        prompt="",  # Not used for ASR
        modality=Modality.AUDIO,
        task_type=TaskType.ASR,
        audio_data="meeting.mp3"
    )
    result = await router.route(req)
    print(f"✅ Selected: {result.selected_model.display_name}")
    print(f"   Modality: {result.selected_model.modalities[0].value}")
    print(f"   Priority: {result.selected_model.priority} (ASR-only)")
    print(f"   Reason: {result.routing_reason}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Routing Summary")
    print("=" * 60)
    print(f"Total models registered: {len(router.models)}")
    print(f"Enabled models: {sum(1 for m in router.models.values() if m.enabled)}")
    print(f"\nModel Health:")
    for name, model in router.models.items():
        if model.enabled:
            status = "🟢" if model.health_score == 1.0 else "🔴"
            print(f"  {status} {model.display_name:30s} ({model.backend.value})")
    
    await router.shutdown()
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_routing())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
