#!/usr/bin/env python3
"""
ASTRA Load Test Runner with SLO validation
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
import subprocess
from typing import Dict, Any, Optional

def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure logging for the test runner"""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('test_runner')

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ASTRA Load Test Runner")
    parser.add_argument(
        "--users", "-u",
        type=int,
        default=10,
        help="Number of concurrent users"
    )
    parser.add_argument(
        "--spawn-rate", "-r",
        type=int,
        default=2,
        help="User spawn rate per second"
    )
    parser.add_argument(
        "--runtime", "-t",
        type=str,
        default="5m",
        help="Test duration (e.g. 30s, 5m, 1h)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8001",
        help="Target host URL"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()

def check_server_ready(host: str, timeout: int = 30) -> bool:
    """Check if server is ready to receive traffic"""
    import requests
    from requests.exceptions import RequestException
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{host}/ready")
            if response.status_code == 200:
                return True
        except RequestException:
            pass
        time.sleep(1)
    return False

def run_load_test(args: argparse.Namespace) -> subprocess.CompletedProcess:
    """Execute Locust load test"""
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", args.host,
        "--users", str(args.users),
        "--spawn-rate", str(args.spawn_rate),
        "--run-time", args.runtime,
        "--headless" if args.headless else "",
        "--csv", f"results/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "--html", "results/report.html"
    ]
    return subprocess.run([arg for arg in cmd if arg], check=True)

def validate_slos(results_file: str, logger: logging.Logger) -> bool:
    """Validate test results against SLOs"""
    try:
        with open(results_file) as f:
            results = json.load(f)
            
        # Extract key metrics
        p95_latency = results.get("stats", {}).get("p95", float('inf'))
        error_rate = results.get("stats", {}).get("fail_ratio", float('inf'))
        first_token = results.get("stats", {}).get("first_token_p95", float('inf'))
        
        # Check against SLOs
        slo_checks = {
            "p95_latency": p95_latency <= 2.5,  # 2.5s for CPU
            "first_token": first_token <= 0.9,   # 900ms for CPU
            "error_rate": error_rate <= 0.02,    # 2% error rate
        }
        
        # Log results
        logger.info("SLO Validation Results:")
        for metric, passed in slo_checks.items():
            logger.info(f"{metric}: {'PASS' if passed else 'FAIL'}")
            
        return all(slo_checks.values())
        
    except Exception as e:
        logger.error(f"Error validating SLOs: {e}")
        return False

def run_chaos_tests() -> bool:
    """Run chaos test scenarios"""
    try:
        result = subprocess.run(
            ["pytest", "tests/test_chaos.py", "-v"],
            check=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Chaos tests failed:\n{e.stdout}\n{e.stderr}")
        return False

def main():
    """Main test runner entry point"""
    args = parse_args()
    logger = setup_logging(args.debug)
    
    # Check server readiness
    logger.info(f"Checking server readiness at {args.host}")
    if not check_server_ready(args.host):
        logger.error("Server not ready")
        sys.exit(1)
    
    try:
        # Run load test
        logger.info("Starting load test")
        result = run_load_test(args)
        
        # Validate results
        results_file = f"results/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_stats.json"
        load_test_passed = validate_slos(results_file, logger)
        
        # Run chaos tests
        logger.info("Starting chaos tests")
        chaos_tests_passed = run_chaos_tests()
        
        if load_test_passed and chaos_tests_passed:
            logger.info("All tests passed successfully")
            sys.exit(0)
        else:
            logger.error("Test suite failed:")
            if not load_test_passed:
                logger.error("- Load test failed SLO validation")
            if not chaos_tests_passed:
                logger.error("- Chaos tests failed")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Tests failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()