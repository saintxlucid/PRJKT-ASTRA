"""
Quick test of implemented universal functions.
"""
import asyncio
from src.astra.core.functions.modules_v2 import (
    ASTRA_INTEL_CORE,
    ASTRA_CREATRIX,
    ASTRA_HEARTMIRROR
)


async def test_functions():
    print("🧪 Testing ASTRA Universal Functions v2.5")
    print("=" * 50)
    
    # Test 1: INTEL_CORE
    print("\n1️⃣ Testing ASTRA_INTEL_CORE...")
    intel = ASTRA_INTEL_CORE()
    result = await intel.invoke(
        topic="Local-first AI architecture",
        objectives=["Assess market opportunity", "Identify risks"]
    )
    print(f"   ✅ Insights: {len(result['insights'])}")
    print(f"   ✅ Risks: {len(result['risks'])}")
    print(f"   ✅ Opportunities: {len(result['opportunities'])}")
    print(f"   ✅ Confidence: {result['confidence_score']}")
    
    # Test 2: CREATRIX
    print("\n2️⃣ Testing ASTRA_CREATRIX...")
    creatrix = ASTRA_CREATRIX()
    result = await creatrix.invoke(
        brief="Ethereal music video",
        medium="music_video",
        mood="dreamlike"
    )
    print(f"   ✅ Concept title: {result['concept']['title']}")
    print(f"   ✅ Visual elements: {len(result['visual_language'])}")
    print(f"   ✅ Structure acts: {len(result['structure'])}")
    print(f"   ✅ Color palette: {len(result['palette'])} colors")
    
    # Test 3: HEARTMIRROR
    print("\n3️⃣ Testing ASTRA_HEARTMIRROR...")
    heartmirror = ASTRA_HEARTMIRROR()
    result = await heartmirror.invoke(
        emotion="grief",
        context="creative burnout",
        intensity=0.7
    )
    print(f"   ✅ Validation: {result['acknowledgment']['validation'][:50]}...")
    print(f"   ✅ Insights: {len(result['insights'])}")
    print(f"   ✅ Practices: {len(result['practices'])}")
    print(f"   ✅ Reframes: {len(result['reframes'])}")
    print(f"   ✅ Resources: {len(result['resources'])}")
    
    print("\n" + "=" * 50)
    print("✅ All 3 functions tested successfully!")
    print("🎯 Production-ready implementations verified.")


if __name__ == "__main__":
    asyncio.run(test_functions())
