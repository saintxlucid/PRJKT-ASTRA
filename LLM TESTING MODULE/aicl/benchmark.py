import time
import asyncio
import statistics
from typing import List, Dict, Callable, Any
from .core import new_msg
from .transport import run_client

class BenchmarkResult:
    """Results from a benchmark test"""
    
    def __init__(self, name: str):
        self.name = name
        self.latencies = []
        self.throughputs = []
        self.errors = 0
        self.success_count = 0
    
    def add_latency(self, latency: float):
        """Add a latency measurement"""
        self.latencies.append(latency)
    
    def add_throughput(self, throughput: float):
        """Add a throughput measurement"""
        self.throughputs.append(throughput)
    
    def add_error(self):
        """Record an error"""
        self.errors += 1
    
    def add_success(self):
        """Record a successful operation"""
        self.success_count += 1
    
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            "name": self.name,
            "total_operations": self.success_count + self.errors,
            "successful_operations": self.success_count,
            "error_rate": self.errors / max(1, self.success_count + self.errors),
            "latency_stats": {
                "mean": statistics.mean(self.latencies) if self.latencies else 0,
                "median": statistics.median(self.latencies) if self.latencies else 0,
                "min": min(self.latencies) if self.latencies else 0,
                "max": max(self.latencies) if self.latencies else 0,
                "stdev": statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0
            } if self.latencies else {},
            "throughput_stats": {
                "mean": statistics.mean(self.throughputs) if self.throughputs else 0,
                "median": statistics.median(self.throughputs) if self.throughputs else 0,
                "min": min(self.throughputs) if self.throughputs else 0,
                "max": max(self.throughputs) if self.throughputs else 0
            } if self.throughputs else {}
        }

class AICLBenchmark:
    """Benchmark AICL performance"""
    
    def __init__(self):
        self.results = []
    
    def benchmark_message_processing(
        self, 
        message_count: int = 1000,
        message_size: int = 1024
    ) -> BenchmarkResult:
        """Benchmark message processing performance"""
        result = BenchmarkResult("Message Processing")
        
        # Create test messages
        test_messages = []
        for i in range(message_count):
            content = "A" * message_size  # Create message of specified size
            msg = new_msg(
                frm=f"sender_{i}",
                to=f"receiver_{i}",
                act="inform",
                payload={
                    "text": {
                        "content": content
                    }
                },
                limits={"tokens": min(message_size // 4, 1024)}
            )
            test_messages.append(msg)
        
        # Benchmark sending messages
        start_time = time.time()
        processed_count = 0
        
        try:
            # This is a simplified benchmark - in reality you'd connect to a server
            for msg in test_messages:
                msg_start = time.time()
                # Simulate message processing
                _ = str(msg)  # Simple processing simulation
                latency = (time.time() - msg_start) * 1000  # Convert to ms
                result.add_latency(latency)
                processed_count += 1
                
                # Calculate throughput periodically
                if processed_count % 100 == 0:
                    elapsed = time.time() - start_time
                    throughput = 100 / elapsed if elapsed > 0 else 0
                    result.add_throughput(throughput)
                    start_time = time.time()  # Reset for next batch
            
            result.add_success()
        except Exception as e:
            print(f"Benchmark error: {e}")
            result.add_error()
        
        self.results.append(result)
        return result
    
    def benchmark_concurrent_connections(
        self,
        connection_count: int = 10,
        messages_per_connection: int = 100
    ) -> BenchmarkResult:
        """Benchmark concurrent connection performance"""
        result = BenchmarkResult("Concurrent Connections")
        
        # This would require a test server to be running
        # For now, we'll simulate the concept
        start_time = time.time()
        
        try:
            # Simulate concurrent operations
            for conn_id in range(connection_count):
                conn_start = time.time()
                for msg_id in range(messages_per_connection):
                    # Simulate message creation and processing
                    msg = new_msg(
                        frm=f"client_{conn_id}",
                        to="server",
                        act="inform",
                        payload={"seq": msg_id}
                    )
                    _ = str(msg)  # Processing simulation
                conn_latency = (time.time() - conn_start) * 1000
                result.add_latency(conn_latency)
            
            total_time = time.time() - start_time
            total_messages = connection_count * messages_per_connection
            throughput = total_messages / total_time if total_time > 0 else 0
            
            result.add_throughput(throughput)
            result.add_success()
        except Exception as e:
            print(f"Concurrent benchmark error: {e}")
            result.add_error()
        
        self.results.append(result)
        return result
    
    def run_all_benchmarks(self) -> List[Dict[str, Any]]:
        """Run all benchmarks and return results"""
        print("Running AICL benchmarks...")
        
        # Run message processing benchmark
        print("Benchmarking message processing...")
        self.benchmark_message_processing()
        
        # Run concurrent connections benchmark
        print("Benchmarking concurrent connections...")
        self.benchmark_concurrent_connections()
        
        # Return all results
        return [result.summary() for result in self.results]
    
    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*50)
        print("AICL BENCHMARK RESULTS")
        print("="*50)
        
        for result in self.results:
            summary = result.summary()
            print(f"\n{summary['name']}:")
            print(f"  Total Operations: {summary['total_operations']}")
            print(f"  Successful: {summary['successful_operations']}")
            print(f"  Error Rate: {summary['error_rate']:.2%}")
            
            if summary['latency_stats']:
                lat_stats = summary['latency_stats']
                print(f"  Latency (ms):")
                print(f"    Mean: {lat_stats['mean']:.2f}")
                print(f"    Median: {lat_stats['median']:.2f}")
                print(f"    Min: {lat_stats['min']:.2f}")
                print(f"    Max: {lat_stats['max']:.2f}")
            
            if summary['throughput_stats']:
                tp_stats = summary['throughput_stats']
                print(f"  Throughput (ops/sec):")
                print(f"    Mean: {tp_stats['mean']:.2f}")
                print(f"    Median: {tp_stats['median']:.2f}")
                print(f"    Max: {tp_stats['max']:.2f}")

# Async version of benchmark
class AsyncAICLBenchmark:
    """Async version of AICL benchmark"""
    
    async def benchmark_async_operations(self, operation_count: int = 1000) -> BenchmarkResult:
        """Benchmark async operations"""
        result = BenchmarkResult("Async Operations")
        
        async def async_operation(i: int):
            """Simulate an async operation"""
            start = time.time()
            # Simulate async work
            await asyncio.sleep(0.001)  # 1ms delay
            latency = (time.time() - start) * 1000
            return latency
        
        start_time = time.time()
        tasks = [async_operation(i) for i in range(operation_count)]
        latencies = await asyncio.gather(*tasks, return_exceptions=True)
        
        for latency in latencies:
            # Check if it's an exception
            if isinstance(latency, Exception):
                result.add_error()
            else:
                # It should be a numeric value (float or int)
                if isinstance(latency, (int, float)):
                    result.add_latency(float(latency))
                    result.add_success()
                else:
                    # Fallback for any unexpected types
                    try:
                        result.add_latency(float(str(latency)))
                        result.add_success()
                    except (ValueError, TypeError):
                        result.add_error()
        
        total_time = time.time() - start_time
        throughput = operation_count / total_time if total_time > 0 else 0
        result.add_throughput(throughput)
        
        return result