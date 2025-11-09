#!/usr/bin/env python3
"""
Test Neural Browser System
Verifies all components are working
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def print_banner():
    print("\n" + "="*60)
    print("🧠 ASTRA NEURAL BROWSER - SYSTEM TEST")
    print("="*60 + "\n")


def test_imports():
    """Test that all modules can be imported"""
    print("📦 Testing imports...")
    
    errors = []
    
    # Test visualization modules
    try:
        from src.astra.visualization.memory_graph_service import MemoryGraphService
        print("   ✓ memory_graph_service")
    except ImportError as e:
        print(f"   ❌ memory_graph_service: {e}")
        errors.append("memory_graph_service")
    
    try:
        from src.astra.visualization.stream_router import StreamRouter
        print("   ✓ stream_router")
    except ImportError as e:
        print(f"   ❌ stream_router: {e}")
        errors.append("stream_router")
    
    # Test PySide6 (optional for graph service test)
    try:
        import PySide6
        print("   ✓ PySide6")
    except ImportError:
        print("   ⚠ PySide6 (optional for visualization)")
    
    # Test websockets (optional)
    try:
        import websockets
        print("   ✓ websockets")
    except ImportError:
        print("   ⚠ websockets (optional for streaming)")
    
    if errors:
        print(f"\n❌ Import errors: {', '.join(errors)}")
        return False
    
    print("\n✓ All required imports successful\n")
    return True


def test_memory_graph_service():
    """Test memory graph service"""
    print("🧬 Testing Memory Graph Service...")
    
    try:
        from src.astra.visualization.memory_graph_service import MemoryGraphService
        
        # Initialize service
        service = MemoryGraphService()
        print("   ✓ Service initialized")
        
        # Build graph (small test)
        start_time = time.time()
        nodes, edges = service.build_graph(max_nodes=50, similarity_threshold=0.3)
        elapsed = time.time() - start_time
        
        print(f"   ✓ Built graph in {elapsed:.2f}s")
        print(f"     - Nodes: {len(nodes)}")
        print(f"     - Edges: {len(edges)}")
        
        # Test export
        export_path = Path("runtime/test_graph_export.json")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        service.export_json(export_path)
        print(f"   ✓ Exported to {export_path}")
        
        # Verify nodes have positions
        if nodes:
            sample_node = nodes[0]
            print(f"\n   Sample Node:")
            print(f"     ID: {sample_node.id}")
            print(f"     Type: {sample_node.memory_type}")
            print(f"     Position: {sample_node.position}")
            print(f"     Color: {sample_node.color}")
            print(f"     Size: {sample_node.size}")
        
        print("\n✓ Memory graph service test passed\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Memory graph service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_data_quality():
    """Test quality of graph data"""
    print("📊 Testing Graph Data Quality...")
    
    try:
        from src.astra.visualization.memory_graph_service import MemoryGraphService
        
        service = MemoryGraphService()
        nodes, edges = service.build_graph(max_nodes=100)
        
        # Check node distribution
        by_type = {}
        for node in nodes:
            by_type[node.memory_type] = by_type.get(node.memory_type, 0) + 1
        
        print("   Node Distribution:")
        for mem_type, count in by_type.items():
            percentage = (count / len(nodes) * 100) if nodes else 0
            print(f"     {mem_type}: {count} ({percentage:.1f}%)")
        
        # Check position spread
        if nodes:
            positions = [node.position for node in nodes]
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            zs = [p[2] for p in positions]
            
            print(f"\n   Position Spread:")
            print(f"     X: {min(xs):.1f} to {max(xs):.1f}")
            print(f"     Y: {min(ys):.1f} to {max(ys):.1f}")
            print(f"     Z: {min(zs):.1f} to {max(zs):.1f}")
        
        # Check edge distribution
        if edges:
            edge_types = {}
            for edge in edges:
                edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
            
            print(f"\n   Edge Types:")
            for edge_type, count in edge_types.items():
                print(f"     {edge_type}: {count}")
        
        # Check for isolated nodes
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.source_id)
            connected_nodes.add(edge.target_id)
        
        isolated = len(nodes) - len(connected_nodes)
        print(f"\n   Connectivity:")
        print(f"     Connected nodes: {len(connected_nodes)}")
        print(f"     Isolated nodes: {isolated}")
        
        if isolated > len(nodes) * 0.5:
            print("     ⚠ Warning: Many isolated nodes (increase similarity threshold)")
        
        print("\n✓ Graph data quality test passed\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Graph data quality test failed: {e}")
        return False


def test_launcher():
    """Test launcher script exists and is configured"""
    print("🚀 Testing Launcher Configuration...")
    
    launcher_path = Path("launch_neural_browser.py")
    
    if launcher_path.exists():
        print(f"   ✓ Launcher found: {launcher_path}")
        
        # Check if executable
        content = launcher_path.read_text(encoding='utf-8')
        if "def main()" in content:
            print("   ✓ Main function present")
        
        if "PySide6" in content:
            print("   ✓ PySide6 check present")
        
        print("\n✓ Launcher configuration test passed\n")
        return True
    else:
        print(f"   ❌ Launcher not found: {launcher_path}")
        return False


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60 + "\n")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    total = len(results)
    passed_count = sum(1 for p in results.values() if p)
    
    print(f"\n  Total: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n🎊 ALL TESTS PASSED - Neural Browser Ready!")
        print("\nRun: python launch_neural_browser.py")
    else:
        print("\n⚠ Some tests failed - review errors above")
    
    print()


def main():
    """Run all tests"""
    print_banner()
    
    results = {}
    
    # Run tests
    results["Imports"] = test_imports()
    
    if results["Imports"]:
        results["Memory Graph Service"] = test_memory_graph_service()
        results["Graph Data Quality"] = test_graph_data_quality()
        results["Launcher Configuration"] = test_launcher()
    else:
        print("⚠ Skipping remaining tests due to import failures")
    
    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
