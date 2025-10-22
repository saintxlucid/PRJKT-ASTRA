"""
ASTRA Memory Performance Tests
Tests performance characteristics of memory operations
"""

import pytest
import time
import statistics
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.astra.core.memory_engine import MemoryEngine
from src.astra.core.metrics.memory_metrics import MemoryMetrics

@pytest.fixture
def memory_engine():
    """Create memory engine instance for testing"""
    engine = MemoryEngine()
    yield engine
    engine.cleanup()  # Cleanup after tests

@pytest.fixture
def metrics():
    """Create metrics instance for testing"""
    return MemoryMetrics()

def measure_operation_time(func):
    """Decorator to measure operation time"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return result, duration
    return wrapper

class TestMemoryPerformance:
    """Performance tests for memory subsystems"""
    
    @pytest.mark.performance
    def test_memory_write_performance(self, memory_engine, metrics):
        """Test write performance for different memory types"""
        memory_types = ['semantic', 'episodic', 'procedural']
        sample_sizes = [10, 100, 1000]
        
        results = {}
        for memory_type in memory_types:
            results[memory_type] = {}
            for size in sample_sizes:
                durations = []
                
                # Generate test data
                test_data = [
                    f"Test data entry {i} for {memory_type} memory"
                    for i in range(size)
                ]
                
                # Measure write time
                with metrics.start_operation_timer(
                    operation_type='write',
                    memory_type=memory_type
                ):
                    for data in test_data:
                        _, duration = measure_operation_time(
                            memory_engine.write
                        )(memory_type, data)
                        durations.append(duration)
                
                # Calculate statistics
                results[memory_type][size] = {
                    'mean': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'std_dev': statistics.stdev(durations),
                    'min': min(durations),
                    'max': max(durations)
                }
                
                # Record metrics
                metrics.record_operation(
                    operation_type='write',
                    memory_type=memory_type,
                    status='success'
                )
                
                # Update memory usage
                metrics.update_memory_usage(
                    memory_type=memory_type,
                    bytes_used=sum(len(d.encode()) for d in test_data)
                )
        
        # Print results
        for memory_type, sizes in results.items():
            print(f"\n{memory_type.title()} Memory Performance:")
            for size, stats in sizes.items():
                print(f"\nSample size: {size}")
                print(f"Mean time: {stats['mean']*1000:.2f}ms")
                print(f"Median time: {stats['median']*1000:.2f}ms")
                print(f"Std dev: {stats['std_dev']*1000:.2f}ms")
                print(f"Min time: {stats['min']*1000:.2f}ms")
                print(f"Max time: {stats['max']*1000:.2f}ms")
    
    @pytest.mark.performance
    def test_memory_read_performance(self, memory_engine, metrics):
        """Test read performance for different memory types"""
        memory_types = ['semantic', 'episodic', 'procedural']
        query_sizes = [1, 10, 100]
        
        results = {}
        for memory_type in memory_types:
            results[memory_type] = {}
            
            # Initialize test data
            test_data = [
                f"Test data entry {i} for {memory_type} memory"
                for i in range(max(query_sizes))
            ]
            for data in test_data:
                memory_engine.write(memory_type, data)
            
            for size in query_sizes:
                durations = []
                
                # Measure read time
                with metrics.start_operation_timer(
                    operation_type='read',
                    memory_type=memory_type
                ):
                    for i in range(size):
                        _, duration = measure_operation_time(
                            memory_engine.read
                        )(memory_type, f"entry {i}")
                        durations.append(duration)
                
                # Calculate statistics
                results[memory_type][size] = {
                    'mean': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'std_dev': statistics.stdev(durations),
                    'min': min(durations),
                    'max': max(durations)
                }
                
                # Record metrics
                metrics.record_operation(
                    operation_type='read',
                    memory_type=memory_type,
                    status='success'
                )
        
        # Print results
        for memory_type, sizes in results.items():
            print(f"\n{memory_type.title()} Memory Read Performance:")
            for size, stats in sizes.items():
                print(f"\nQuery size: {size}")
                print(f"Mean time: {stats['mean']*1000:.2f}ms")
                print(f"Median time: {stats['median']*1000:.2f}ms")
                print(f"Std dev: {stats['std_dev']*1000:.2f}ms")
                print(f"Min time: {stats['min']*1000:.2f}ms")
                print(f"Max time: {stats['max']*1000:.2f}ms")
    
    @pytest.mark.performance
    def test_cache_performance(self, memory_engine, metrics):
        """Test cache hit/miss performance"""
        memory_types = ['semantic', 'episodic', 'procedural']
        
        for memory_type in memory_types:
            # Write test data
            test_data = [
                f"Cache test data {i} for {memory_type} memory"
                for i in range(100)
            ]
            for data in test_data:
                memory_engine.write(memory_type, data)
            
            # Test cache performance
            cache_hits = 0
            total_queries = 1000
            durations = []
            
            for i in range(total_queries):
                # Alternate between cached and uncached queries
                query = f"test data {i % 50}"
                
                with metrics.start_operation_timer(
                    operation_type='read',
                    memory_type=memory_type
                ):
                    result, duration = measure_operation_time(
                        memory_engine.read
                    )(memory_type, query)
                    
                    if result:  # Cache hit
                        cache_hits += 1
                        metrics.record_cache_result(memory_type, hit=True)
                    else:  # Cache miss
                        metrics.record_cache_result(memory_type, hit=False)
                    
                    durations.append(duration)
            
            # Calculate cache statistics
            hit_ratio = cache_hits / total_queries
            avg_duration = statistics.mean(durations)
            
            print(f"\n{memory_type.title()} Memory Cache Performance:")
            print(f"Cache hit ratio: {hit_ratio:.2%}")
            print(f"Average query time: {avg_duration*1000:.2f}ms")
            print(f"Total queries: {total_queries}")
            
            # Record final metrics
            metrics.record_query_complexity(
                memory_type=memory_type,
                operation_type='cache_test',
                complexity_score=1.0
            )