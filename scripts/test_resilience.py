"""
Resilience testing script for ASTRA components.

This script runs failure drills to verify:
- Circuit breaker behavior
- Retry mechanisms
- Recovery procedures
- Telemetry during failures
"""
import os
import sys
import time
import signal
import subprocess
import argparse
import structlog
from pathlib import Path
from typing import Optional

import psutil
import docker

from astra.resilience.core import CircuitBreaker, CircuitConfig, health
from astra.store.qdrant_store import QdrantStore
from astra.embed.bge import BGEM3Embedder
from astra.rag.pipeline import MultiRAGPipeline
from astra.telemetry.events import EventLogger

logger = structlog.get_logger()

def find_process(name: str) -> Optional[psutil.Process]:
    """Find process by name."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == name:
            return proc
    return None

def kill_qdrant():
    """Kill Qdrant process/container."""
    # Try process first
    proc = find_process('qdrant')
    if proc:
        proc.kill()
        return
        
    # Try Docker
    client = docker.from_env()
    for container in client.containers.list():
        if 'qdrant' in container.name:
            container.kill()
            return
            
    raise Exception("Qdrant process/container not found")

def test_qdrant_failure(pipeline: MultiRAGPipeline):
    """Test Qdrant failure handling."""
    logger.info("testing_qdrant_failure")
    
    # Configure circuit breaker
    config = CircuitConfig(
        failure_threshold=3,
        reset_timeout=10.0
    )
    breaker = CircuitBreaker("qdrant", config)
    
    # Verify initial state
    result = breaker.call(
        lambda: pipeline.retrieve("test query", k=5)
    )
    assert len(result) > 0
    assert health.is_healthy("qdrant")
    
    # Kill Qdrant
    kill_qdrant()
    logger.info("qdrant_killed")
    
    # Verify circuit opens
    try:
        breaker.call(
            lambda: pipeline.retrieve("test query", k=5)
        )
    except Exception as e:
        logger.info("expected_failure", error=str(e))
    
    assert not health.is_healthy("qdrant")
    assert breaker.state == "open"
    
    # Restart Qdrant (assumes systemd service)
    subprocess.run(
        ["sudo", "systemctl", "start", "qdrant"],
        check=True
    )
    logger.info("qdrant_restarted")
    
    # Wait for reset
    time.sleep(config.reset_timeout)
    
    # Verify recovery
    result = breaker.call(
        lambda: pipeline.retrieve("test query", k=5)
    )
    assert len(result) > 0
    assert health.is_healthy("qdrant")
    assert breaker.state == "closed"

def simulate_gpu_error(embedder: BGEM3Embedder):
    """Simulate GPU error by setting invalid device."""
    embedder.device = "invalid_device"

def restore_gpu(embedder: BGEM3Embedder):
    """Restore GPU access."""
    embedder.device = "cuda"

def test_embedder_failure(pipeline: MultiRAGPipeline):
    """Test embedder failure handling."""
    logger.info("testing_embedder_failure")
    
    # Configure circuit breaker
    config = CircuitConfig(
        failure_threshold=3,
        reset_timeout=5.0,
        max_retries=2
    )
    breaker = CircuitBreaker("embedder", config)
    
    # Get embedder from pipeline
    embedder = pipeline.dense_index.embedder
    
    # Verify initial state
    result = breaker.call(
        lambda: embedder.embed_query("test")
    )
    assert result is not None
    assert health.is_healthy("embedder")
    
    # Simulate GPU error
    simulate_gpu_error(embedder)
    logger.info("gpu_error_simulated")
    
    # Verify circuit opens
    try:
        breaker.call(
            lambda: embedder.embed_query("test")
        )
    except Exception as e:
        logger.info("expected_failure", error=str(e))
    
    assert not health.is_healthy("embedder")
    assert breaker.state == "open"
    
    # Restore GPU
    restore_gpu(embedder)
    logger.info("gpu_restored")
    
    # Wait for reset
    time.sleep(config.reset_timeout)
    
    # Verify recovery
    result = breaker.call(
        lambda: embedder.embed_query("test")
    )
    assert result is not None
    assert health.is_healthy("embedder")
    assert breaker.state == "closed"

def main():
    parser = argparse.ArgumentParser(
        description="Run ASTRA resilience tests"
    )
    parser.add_argument(
        "--config",
        default="config/rag.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--test",
        choices=["qdrant", "embedder", "all"],
        default="all",
        help="Which failure test to run"
    )
    args = parser.parse_args()

    try:
        # Set up logging
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        event_logger = EventLogger(
            log_dir=str(log_dir),
            rotation_bytes=1048576,
            max_files=5
        )
        
        # Create pipeline
        pipeline = MultiRAGPipeline.from_config_file(args.config)
        
        # Run requested tests
        if args.test in ["qdrant", "all"]:
            test_qdrant_failure(pipeline)
            
        if args.test in ["embedder", "all"]:
            test_embedder_failure(pipeline)
            
        logger.info("resilience_tests_complete")
        return 0
        
    except Exception as e:
        logger.error("resilience_tests_failed", error=str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())