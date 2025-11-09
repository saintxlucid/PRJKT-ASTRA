"""
llama.cpp Flag Benchmark Helper

Quick benchmark tool to test llama.cpp performance with different flags.
Helps identify optimal --threads, --batch, and --ubatch settings for your CPU.

Usage:
    # 1. Start llama.cpp server with specific flags:
    llama-server.exe --model models\gpt-oss-20b-q4.gguf --threads 8 --batch 512 --ctx-size 2048
    
    # 2. Run benchmark (default: 5 samples):
    python scripts\benchmark_llama_flags.py
    
    # 3. Change flags, restart server, repeat
    # 4. Compare mean/p95 latency across configurations

Environment Variables:
    LLAMA_URL - llama.cpp server URL (default: http://127.0.0.1:8001)
    BENCHMARK_SAMPLES - Number of samples (default: 5)

Output:
    JSON with mean, p95, and raw latency samples
"""

import asyncio
import json
import os
import sys
import time
from typing import List

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed", file=sys.stderr)
    print("Install: pip install httpx", file=sys.stderr)
    sys.exit(1)

# Configuration
LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:8001")
BENCHMARK_SAMPLES = int(os.getenv("BENCHMARK_SAMPLES", "5"))

# Test prompt (small, representative)
TEST_PROMPT = "Write one factual sentence about the Moon."
MAX_TOKENS = 64  # Keep small for quick turnaround


async def run_single_inference(client: httpx.AsyncClient) -> float:
    """
    Run single inference and return latency.
    
    Args:
        client: httpx AsyncClient
        
    Returns:
        Latency in seconds
    """
    start = time.perf_counter()
    
    response = await client.post(
        f"{LLAMA_URL}/v1/completions",
        json={
            "prompt": TEST_PROMPT,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.7,
        },
        timeout=45.0,
    )
    response.raise_for_status()
    
    elapsed = time.perf_counter() - start
    return elapsed


async def run_benchmark(samples: int = BENCHMARK_SAMPLES) -> dict:
    """
    Run benchmark with N samples.
    
    Args:
        samples: Number of inference runs
        
    Returns:
        Dictionary with statistics
    """
    latencies: List[float] = []
    
    async with httpx.AsyncClient() as client:
        # Health check first
        try:
            health = await client.get(f"{LLAMA_URL}/health", timeout=5.0)
            health.raise_for_status()
        except Exception as e:
            return {
                "error": f"llama.cpp server not responding: {e}",
                "url": LLAMA_URL,
            }
        
        # Run samples sequentially (avoid cache effects)
        for i in range(samples):
            try:
                latency = await run_single_inference(client)
                latencies.append(latency)
                print(f"Sample {i + 1}/{samples}: {latency:.3f}s", file=sys.stderr)
            except Exception as e:
                print(f"Sample {i + 1} failed: {e}", file=sys.stderr)
                continue
    
    if not latencies:
        return {"error": "All samples failed", "url": LLAMA_URL}
    
    # Calculate statistics
    latencies_sorted = sorted(latencies)
    mean = sum(latencies) / len(latencies)
    p50 = latencies_sorted[len(latencies_sorted) // 2]
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
    
    return {
        "url": LLAMA_URL,
        "samples": len(latencies),
        "mean_seconds": round(mean, 3),
        "p50_seconds": round(p50, 3),
        "p95_seconds": round(p95, 3),
        "p99_seconds": round(p99, 3),
        "min_seconds": round(min(latencies), 3),
        "max_seconds": round(max(latencies), 3),
        "raw_samples": [round(x, 3) for x in latencies],
    }


def main():
    """Main entry point"""
    print(f"Benchmarking llama.cpp @ {LLAMA_URL}", file=sys.stderr)
    print(f"Running {BENCHMARK_SAMPLES} samples...\n", file=sys.stderr)
    
    result = asyncio.run(run_benchmark(BENCHMARK_SAMPLES))
    
    # Print JSON result
    print(json.dumps(result, indent=2))
    
    # Exit code
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
