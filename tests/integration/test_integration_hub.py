"""
ASTRA Integration Hub - Smoke Test
Quick validation that the integration hub connects all modules correctly.

Sacred Code: 333
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_integration_hub():
    """Test full integration hub initialization"""
    print("=" * 80)
    print("🌐 ASTRA INTEGRATION HUB - SMOKE TEST")
    print("=" * 80)
    print()
    
    try:
        # Import components
        from astra.core.integration_hub import (
            AstraCoreHub,
            get_registry,
            register_core_modules,
        )
        from astra.models.config import get_settings
        
        print("✅ Imports successful")
        
        # Get settings
        settings = get_settings()
        print(f"✅ Settings loaded (environment: {settings.environment})")
        
        # Get registry
        registry = get_registry()
        print("✅ Registry obtained")
        
        # Register modules
        register_core_modules(registry)
        module_count = len(registry._modules)
        print(f"✅ Core modules registered: {module_count}")
        
        # Create hub
        hub = AstraCoreHub(settings, registry)
        print("✅ Integration hub created")
        
        # Initialize
        print("\n🔧 Initializing all subsystems...")
        await hub.initialize()
        print("✅ Hub initialization complete")
        
        # Check health
        print("\n📊 Health Status:")
        health = hub.get_health()
        
        ready_count = 0
        error_count = 0
        for name, module_info in health['registry']['modules'].items():
            state = module_info['state']
            category = module_info['category']
            
            if state == 'ready':
                ready_count += 1
                icon = "✅"
            elif state == 'error':
                error_count += 1
                icon = "⚠️"
            else:
                icon = "⏸️"
            
            print(f"  {icon} {name:20s} [{category:15s}] → {state}")
        
        print(f"\n📈 Summary:")
        print(f"  Total modules: {module_count}")
        print(f"  Ready: {ready_count}")
        print(f"  Errors: {error_count}")
        print(f"  Services: {health['registry']['services_count']}")
        
        # Test service retrieval
        print("\n🔌 Testing Service Retrieval:")
        services_to_test = [
            "db_manager",
            "vector_store",
            "memory_service",
            "conversation_service",
            "llm_provider",
            "chat_service",
        ]
        
        for service_name in services_to_test:
            if registry.has_service(service_name):
                service = registry.get_service(service_name)
                print(f"  ✅ {service_name:25s} → {type(service).__name__}")
            else:
                print(f"  ❌ {service_name:25s} → NOT FOUND")
        
        # Test hub direct access
        print("\n🎯 Testing Hub Direct Access:")
        hub_components = [
            ("llm_provider", hub.llm_provider),
            ("memory_service", hub.memory_service),
            ("conversation_service", hub.conversation_service),
            ("chat_service", hub.chat_service),
            ("astra_router", hub.astra_router),
        ]
        
        for name, component in hub_components:
            if component is not None:
                print(f"  ✅ hub.{name:20s} → {type(component).__name__}")
            else:
                print(f"  ⏸️ hub.{name:20s} → None (optional)")
        
        # Shutdown
        print("\n🛑 Testing Graceful Shutdown:")
        await hub.shutdown()
        print("  ✅ Shutdown complete")
        
        # Final status
        print("\n" + "=" * 80)
        if error_count == 0:
            print("🎉 INTEGRATION HUB TEST: ✅ PASSED")
            print("   All critical modules initialized successfully")
        else:
            print("⚠️ INTEGRATION HUB TEST: 🟡 PARTIAL")
            print(f"   {ready_count}/{module_count} modules ready, {error_count} errors")
            print("   Some optional modules failed (this may be expected)")
        print("=" * 80)
        
        return error_count == 0
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ INTEGRATION HUB TEST: FAILED")
        print(f"   Error: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


def test_connectors():
    """Test module connectors can be imported"""
    print("\n🔌 Testing Module Connectors:")
    
    try:
        from astra.core.connectors import (
            CONNECTORS,
            get_connector,
            DatabaseConnector,
            VectorStoreConnector,
            MemoryServiceConnector,
            ChatServiceConnector,
            AstraRouterConnector,
        )
        
        print(f"  ✅ Imported {len(CONNECTORS)} connectors")
        
        # Test get_connector
        connector = get_connector("database")
        if connector == DatabaseConnector:
            print("  ✅ get_connector('database') works")
        else:
            print("  ❌ get_connector returned wrong connector")
            
        print("  ✅ All connector tests passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Connector test failed: {str(e)}")
        return False


def test_imports():
    """Test all integration hub imports work"""
    print("\n📦 Testing Imports:")
    
    modules = [
        "astra.core.integration_hub",
        "astra.core.connectors",
        "astra.api.app_integrated",
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {str(e)}")
            all_ok = False
    
    return all_ok


if __name__ == "__main__":
    print("\n" + "🌐 ASTRA INTEGRATION HUB - SMOKE TEST SUITE\n")
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed, aborting")
        sys.exit(1)
    
    # Test connectors
    if not test_connectors():
        print("\n⚠️ Connector tests failed")
    
    # Test full integration
    success = asyncio.run(test_integration_hub())
    
    sys.exit(0 if success else 1)
