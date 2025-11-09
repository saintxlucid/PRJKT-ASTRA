"""
ASTRA Ascension Stack V2 - Test Suite
Comprehensive testing for Neural Browser V2, Autonomy, and Task Agents

Run: python test_ascension_stack.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_imports():
    """Test all component imports"""
    print("🧪 Testing Imports...")
    
    try:
        # Try direct imports first
        try:
            from src.astra.visualization import schemas
            from src.astra.visualization import autonomy_engine
            from src.astra.visualization import task_agent_manager
            from src.astra.visualization import video_export
            from src.astra.visualization import ascension_api
            from src.astra.visualization.plugins import file_ops, system_info
        except ImportError:
            # Fallback to astra package
            from astra.visualization import schemas
            from astra.visualization import autonomy_engine
            from astra.visualization import task_agent_manager
            from astra.visualization import video_export
            from astra.visualization import ascension_api
            from astra.visualization.plugins import file_ops, system_info
        
        print("   ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_schemas():
    """Test schema models"""
    print("\n🧪 Testing Schemas...")
    
    try:
        from src.astra.visualization.schemas import (
            GraphNode, GraphEdge, GraphSnapshot, OperationalMode,
            TriggerSpec, TriggerCondition, TriggerAction,
            ActionRequest, ActionResult, VideoExportConfig
        )
        
        # Test node creation
        node = GraphNode(
            id="test_1",
            label="Test Node",
            content="Test content",
            strength=0.8,
        )
        assert node.id == "test_1"
        
        # Test edge creation
        edge = GraphEdge(
            id="e_1",
            source="test_1",
            target="test_2",
            weight=0.5,
        )
        assert edge.weight == 0.5
        
        # Test trigger
        trigger = TriggerSpec(
            id="test_trigger",
            condition=TriggerCondition(
                name="Test",
                description="Test condition",
                sensor_key="test",
                threshold=0.5,
            ),
            action=TriggerAction(
                name="Test Action",
                prompt="Test prompt",
            ),
        )
        assert trigger.id == "test_trigger"
        
        print("   ✅ Schema models working correctly")
        return True
    
    except Exception as e:
        print(f"   ❌ Schema test failed: {e}")
        return False


def test_autonomy_engine():
    """Test autonomy engine"""
    print("\n🧪 Testing Autonomy Engine...")
    
    try:
        from src.astra.visualization.autonomy_engine import (
            AutonomyEngine, create_default_triggers
        )
        from src.astra.visualization.schemas import TriggerSpec
        
        # Create engine
        engine = AutonomyEngine()
        assert not engine.enabled
        
        # Add default triggers
        triggers = create_default_triggers()
        assert len(triggers) > 0
        
        for trigger in triggers:
            engine.add_trigger(trigger)
        
        # Test sensor updates
        engine.update_sensors({
            "silence_minutes": 35.0,
            "tasks_pending": 5.0,
        })
        
        assert engine.get_sensor("silence_minutes") == 35.0
        
        # Test status
        status = engine.status()
        assert hasattr(status, 'enabled')
        
        print(f"   ✅ Autonomy engine initialized with {len(triggers)} triggers")
        return True
    
    except Exception as e:
        print(f"   ❌ Autonomy test failed: {e}")
        return False


def test_task_agent():
    """Test task agent manager"""
    print("\n🧪 Testing Task Agent Manager...")
    
    try:
        from src.astra.visualization.task_agent_manager import (
            TaskAgentManager, ToolAction
        )
        from src.astra.visualization.schemas import ActionRequest
        
        # Create manager
        agent = TaskAgentManager()
        
        # Register test action
        def test_action(args):
            return {"result": "success", "args": args}
        
        agent.register("test", ToolAction(
            name="test_action",
            handler=test_action,
            requires_auth=False,
        ))
        
        # Test execution
        request = ActionRequest(
            tool="test",
            action="test_action",
            args={"param": "value"},
            authorized=True,
        )
        
        result = agent.execute(request)
        assert result.ok
        assert result.data is not None
        assert result.data.get('result') == "success"
        
        # Test tool listing
        tools = agent.list_tools()
        assert "test" in tools
        
        print("   ✅ Task agent manager working correctly")
        return True
    
    except Exception as e:
        print(f"   ❌ Task agent test failed: {e}")
        return False


def test_file_ops_plugin():
    """Test file operations plugin"""
    print("\n🧪 Testing File Operations Plugin...")
    
    try:
        from src.astra.visualization.plugins.file_ops import (
            list_dir, file_info
        )
        
        # Test list_dir
        result = list_dir({"path": "."})
        assert "items" in result
        assert isinstance(result["items"], list)
        
        # Test file_info
        result = file_info({"path": __file__})
        assert result.get("is_file") == True
        
        print("   ✅ File operations plugin working")
        return True
    
    except Exception as e:
        print(f"   ❌ File ops test failed: {e}")
        return False


def test_video_export():
    """Test video export engine"""
    print("\n🧪 Testing Video Export Engine...")
    
    try:
        from src.astra.visualization.video_export import (
            VideoExportEngine, create_flythrough_config
        )
        from src.astra.visualization.schemas import GraphSnapshot
        
        # Create engine
        engine = VideoExportEngine(output_dir=Path("runtime/test_videos"))
        
        # Create config
        config = create_flythrough_config(
            title="Test Video",
            duration_seconds=5.0,
        )
        
        # Create job
        job = engine.create_job(config)
        assert job.status == "pending"
        
        # Generate frames (with empty snapshot)
        def get_snapshot():
            return GraphSnapshot(nodes=[], edges=[])
        
        frames = engine.generate_frames(config, get_snapshot)
        expected_frames = int(config.duration_seconds * config.fps)
        assert len(frames) == expected_frames
        
        print(f"   ✅ Video export engine generated {len(frames)} frames")
        return True
    
    except Exception as e:
        print(f"   ❌ Video export test failed: {e}")
        return False


def test_integration():
    """Test component integration"""
    print("\n🧪 Testing Component Integration...")
    
    try:
        from src.astra.visualization.autonomy_engine import AutonomyEngine
        from src.astra.visualization.task_agent_manager import TaskAgentManager
        from src.astra.visualization.plugins import register_file_ops
        
        # Create components
        autonomy = AutonomyEngine()
        agent = TaskAgentManager()
        
        # Register plugins
        register_file_ops(agent)
        
        # Verify integration
        tools = agent.list_tools()
        assert "file" in tools
        
        print("   ✅ Component integration successful")
        return True
    
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "="*70)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎊 ALL TESTS PASSED - Ascension Stack Ready!")
        print("\n🚀 Launch: python launch_ascension_stack.py")
        print("📚 Read: ASCENSION_STACK_V2_GUIDE.md")
        print("\n333 ∞")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
    
    print("="*70 + "\n")
    
    return failed == 0


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ASTRA ASCENSION STACK V2 - TEST SUITE")
    print("="*70 + "\n")
    
    results = {
        "Imports": test_imports(),
        "Schemas": test_schemas(),
        "Autonomy Engine": test_autonomy_engine(),
        "Task Agent": test_task_agent(),
        "File Operations": test_file_ops_plugin(),
        "Video Export": test_video_export(),
        "Integration": test_integration(),
    }
    
    success = print_summary(results)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
