"""
ASTRA Fusion Test Suite - Text Latency Regression
==================================================
Sacred Code: 333

Tests that fusion pipeline does not introduce significant latency
regression for pure text generation (p95 within ±5%).
"""

import sys
import time
from pathlib import Path
from typing import List
import pytest
import statistics

# Add fusion pipeline to path
fusion_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/ops/fusion_pipeline/scripts")
sys.path.insert(0, str(fusion_path))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "runtime_hook",
        fusion_path / "05_runtime_hook_example.py"
    )
    runtime_hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime_hook)
    AstraRouter = runtime_hook.AstraRouter
except Exception as e:
    pytest.skip(f"AstraRouter not available: {e}", allow_module_level=True)


class MockLLM:
    """Mock LLM with realistic latency simulation."""
    
    def __init__(self, base_latency_ms=50):
        self.base_latency_ms = base_latency_ms
        self.call_count = 0
    
    def generate(self, prompt, max_tokens=512):
        self.call_count += 1
        # Simulate LLM processing time
        time.sleep(self.base_latency_ms / 1000.0)
        return f"[MOCK LLM RESPONSE {self.call_count}]"


class MockToolBus:
    """Mock Tool Bus."""
    
    def execute(self, tool, payload):
        return "[MOCK TOOL RESPONSE]"


class MockMemory:
    """Mock Memory service with realistic retrieval time."""
    
    def __init__(self, retrieval_latency_ms=5):
        self.retrieval_latency_ms = retrieval_latency_ms
    
    def retrieve_relevant(self, query, top_k=6):
        # Simulate memory retrieval
        time.sleep(self.retrieval_latency_ms / 1000.0)
        return "<memory>Sacred Code 333 context</memory>"


class MockConsent:
    """Mock Consent manager."""
    
    def allowed(self, action):
        return True


def measure_latency(func, iterations=100) -> List[float]:
    """Measure function latency over multiple iterations."""
    latencies = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms
    
    return latencies


def calculate_percentile(data: List[float], percentile: int) -> float:
    """Calculate percentile from data."""
    return statistics.quantiles(data, n=100)[percentile - 1]


class TestTextLatencyRegression:
    """Test suite for latency regression analysis."""
    
    ITERATIONS = 50  # Number of iterations for statistical significance
    ALLOWED_REGRESSION_PERCENT = 5.0  # ±5% allowed
    
    def test_router_overhead_minimal(self):
        """Test that router adds minimal overhead to text generation."""
        # Baseline: Direct LLM call
        mock_llm_baseline = MockLLM(base_latency_ms=50)
        
        def baseline_call():
            mock_llm_baseline.generate("Test prompt")
        
        baseline_latencies = measure_latency(baseline_call, self.ITERATIONS)
        baseline_p95 = calculate_percentile(baseline_latencies, 95)
        
        # With Router
        mock_llm_router = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory(retrieval_latency_ms=5)
        mock_consent = MockConsent()
        
        router = AstraRouter(
            llm=mock_llm_router,
            tool_bus=mock_tool_bus,
            memory=mock_memory,
            consent=mock_consent
        )
        
        def router_call():
            router.handle("Test prompt without special tokens")
        
        router_latencies = measure_latency(router_call, self.ITERATIONS)
        router_p95 = calculate_percentile(router_latencies, 95)
        
        # Calculate regression percentage
        regression_percent = ((router_p95 - baseline_p95) / baseline_p95) * 100
        
        # Assert: Regression within acceptable bounds
        assert regression_percent <= self.ALLOWED_REGRESSION_PERCENT, \
               f"Latency regression {regression_percent:.2f}% exceeds {self.ALLOWED_REGRESSION_PERCENT}% threshold\n" \
               f"Baseline p95: {baseline_p95:.2f}ms, Router p95: {router_p95:.2f}ms"
    
    def test_memory_augmentation_overhead_acceptable(self):
        """Test that memory retrieval overhead is acceptable."""
        mock_llm = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_consent = MockConsent()
        
        # Fast memory
        fast_memory = MockMemory(retrieval_latency_ms=1)
        router_fast = AstraRouter(mock_llm, mock_tool_bus, fast_memory, mock_consent)
        
        # Slow memory
        slow_memory = MockMemory(retrieval_latency_ms=20)
        router_slow = AstraRouter(MockLLM(50), mock_tool_bus, slow_memory, mock_consent)
        
        # Measure
        fast_latencies = measure_latency(lambda: router_fast.handle("Test"), 30)
        slow_latencies = measure_latency(lambda: router_slow.handle("Test"), 30)
        
        fast_p95 = calculate_percentile(fast_latencies, 95)
        slow_p95 = calculate_percentile(slow_latencies, 95)
        
        # Difference should be approximately the memory latency difference
        memory_overhead = slow_p95 - fast_p95
        
        # Should be close to 20ms - 1ms = ~19ms
        assert 15 < memory_overhead < 25, \
               f"Memory overhead unexpected: {memory_overhead:.2f}ms (expected ~19ms)"
    
    def test_mode_extraction_negligible_overhead(self):
        """Test that mode extraction adds negligible overhead."""
        mock_llm = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory(retrieval_latency_ms=5)
        mock_consent = MockConsent()
        
        router = AstraRouter(mock_llm, mock_tool_bus, mock_memory, mock_consent)
        
        # Without mode tags
        no_mode_latencies = measure_latency(
            lambda: router.handle("Test prompt"),
            30
        )
        
        # With mode tags
        with_mode_latencies = measure_latency(
            lambda: router.handle("<|mode_start|>COGNITION<|mode_end|> Test prompt"),
            30
        )
        
        no_mode_p50 = statistics.median(no_mode_latencies)
        with_mode_p50 = statistics.median(with_mode_latencies)
        
        overhead = with_mode_p50 - no_mode_p50
        
        # Mode extraction should add < 1ms overhead
        assert overhead < 1.0, \
               f"Mode extraction overhead too high: {overhead:.2f}ms"
    
    def test_consistency_across_runs(self):
        """Test that latency is consistent across multiple runs."""
        mock_llm = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory(retrieval_latency_ms=5)
        mock_consent = MockConsent()
        
        router = AstraRouter(mock_llm, mock_tool_bus, mock_memory, mock_consent)
        
        latencies = measure_latency(
            lambda: router.handle("Consistent test prompt"),
            100
        )
        
        mean = statistics.mean(latencies)
        stdev = statistics.stdev(latencies)
        
        # Coefficient of variation should be low (< 20%)
        cv = (stdev / mean) * 100
        
        assert cv < 20.0, \
               f"High variance in latency: CV={cv:.2f}% (mean={mean:.2f}ms, stdev={stdev:.2f}ms)"
    
    def test_special_token_detection_fast(self):
        """Test that special token detection is fast."""
        mock_llm = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory(retrieval_latency_ms=5)
        mock_consent = MockConsent()
        
        router = AstraRouter(mock_llm, mock_tool_bus, mock_memory, mock_consent)
        
        # Long prompt with no special tokens (worst case for regex)
        long_prompt = "Test prompt " * 1000  # 2000 words
        
        start = time.perf_counter()
        router.handle(long_prompt)
        end = time.perf_counter()
        
        total_time_ms = (end - start) * 1000
        
        # Even with long prompt, should complete in reasonable time
        # (50ms LLM + 5ms memory + router overhead)
        assert total_time_ms < 100, \
               f"Long prompt processing too slow: {total_time_ms:.2f}ms"


class TestLatencyStatistics:
    """Test latency statistical analysis."""
    
    def test_p50_p95_p99_calculation(self):
        """Test percentile calculations are correct."""
        # Create known distribution
        data = list(range(1, 101))  # 1-100
        
        p50 = calculate_percentile(data, 50)
        p95 = calculate_percentile(data, 95)
        p99 = calculate_percentile(data, 99)
        
        # Check approximate values
        assert 48 <= p50 <= 52, f"p50 calculation incorrect: {p50}"
        assert 93 <= p95 <= 97, f"p95 calculation incorrect: {p95}"
        assert 97 <= p99 <= 100, f"p99 calculation incorrect: {p99}"
    
    def test_latency_measurement_accuracy(self):
        """Test that latency measurement is accurate."""
        def known_delay():
            time.sleep(0.010)  # 10ms
        
        latencies = measure_latency(known_delay, 10)
        mean_latency = statistics.mean(latencies)
        
        # Should be close to 10ms (within 2ms tolerance for system jitter)
        assert 8 < mean_latency < 12, \
               f"Latency measurement inaccurate: {mean_latency:.2f}ms (expected ~10ms)"


class TestPerformanceBenchmark:
    """Benchmark suite for performance documentation."""
    
    @pytest.mark.benchmark
    def test_baseline_llm_performance(self):
        """Benchmark: Pure LLM performance (no router)."""
        mock_llm = MockLLM(base_latency_ms=50)
        
        latencies = measure_latency(
            lambda: mock_llm.generate("Test"),
            100
        )
        
        print(f"\n{'='*60}")
        print(f"Baseline LLM Performance (no router)")
        print(f"{'='*60}")
        print(f"p50: {statistics.median(latencies):.2f}ms")
        print(f"p95: {calculate_percentile(latencies, 95):.2f}ms")
        print(f"p99: {calculate_percentile(latencies, 99):.2f}ms")
        print(f"mean: {statistics.mean(latencies):.2f}ms")
        print(f"stdev: {statistics.stdev(latencies):.2f}ms")
    
    @pytest.mark.benchmark
    def test_router_text_performance(self):
        """Benchmark: Router with text (memory-augmented)."""
        mock_llm = MockLLM(base_latency_ms=50)
        mock_tool_bus = MockToolBus()
        mock_memory = MockMemory(retrieval_latency_ms=5)
        mock_consent = MockConsent()
        
        router = AstraRouter(mock_llm, mock_tool_bus, mock_memory, mock_consent)
        
        latencies = measure_latency(
            lambda: router.handle("Test prompt"),
            100
        )
        
        print(f"\n{'='*60}")
        print(f"Router Text Performance (with memory)")
        print(f"{'='*60}")
        print(f"p50: {statistics.median(latencies):.2f}ms")
        print(f"p95: {calculate_percentile(latencies, 95):.2f}ms")
        print(f"p99: {calculate_percentile(latencies, 99):.2f}ms")
        print(f"mean: {statistics.mean(latencies):.2f}ms")
        print(f"stdev: {statistics.stdev(latencies):.2f}ms")
        print(f"Sacred Code: 333")


if __name__ == "__main__":
    # Run with benchmarks
    pytest.main([__file__, "-v", "--tb=short", "-m", "benchmark", "-s"])
