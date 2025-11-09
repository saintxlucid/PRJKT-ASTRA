#!/usr/bin/env python3
"""
ASTRA Go-Live Validation Suite
Runs comprehensive pre-deployment checks and generates a report.
"""

import asyncio
import aiohttp
import time
import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List
import subprocess
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GoLiveValidator:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "slos": {},
            "recommendations": []
        }
        
    async def check_health_endpoints(self) -> bool:
        """Validate health check endpoints"""
        async with aiohttp.ClientSession() as session:
            # Check /live
            try:
                async with session.get(f"{self.base_url}/live") as resp:
                    live_ok = resp.status == 200
                    live_data = await resp.json()
                    self.results["checks"]["live"] = {
                        "status": "pass" if live_ok else "fail",
                        "response": live_data
                    }
            except Exception as e:
                logger.error(f"Live check failed: {e}")
                self.results["checks"]["live"] = {"status": "fail", "error": str(e)}
                return False

            # Check /ready
            try:
                async with session.get(f"{self.base_url}/ready") as resp:
                    ready_ok = resp.status == 200
                    ready_data = await resp.json()
                    self.results["checks"]["ready"] = {
                        "status": "pass" if ready_ok else "fail",
                        "response": ready_data
                    }
            except Exception as e:
                logger.error(f"Ready check failed: {e}")
                self.results["checks"]["ready"] = {"status": "fail", "error": str(e)}
                return False

            # Check /health/full
            try:
                async with session.get(f"{self.base_url}/health/full") as resp:
                    health_ok = resp.status == 200
                    health_data = await resp.json()
                    self.results["checks"]["health_full"] = {
                        "status": "pass" if health_ok else "fail",
                        "response": health_data
                    }
                    
                    # Validate component health
                    components_ok = all(
                        comp["status"] == "healthy" 
                        for comp in health_data.get("components", {}).values()
                    )
                    if not components_ok:
                        self.results["recommendations"].append(
                            "Some components are not healthy - check /health/full"
                        )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.results["checks"]["health_full"] = {"status": "fail", "error": str(e)}
                return False

        return all(check["status"] == "pass" for check in self.results["checks"].values())

    async def validate_answer_endpoint(self) -> bool:
        """Test /answer endpoint for correct response format and citations"""
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "query": "What is ASTRA?",
                    "max_tokens": 100
                }
                async with session.post(
                    f"{self.base_url}/answer",
                    json=payload
                ) as resp:
                    answer_ok = resp.status == 200
                    answer_data = await resp.json()
                    
                    # Validate response structure
                    required_fields = ["answer", "latency_ms", "citations"]
                    fields_ok = all(field in answer_data for field in required_fields)
                    
                    self.results["checks"]["answer_endpoint"] = {
                        "status": "pass" if (answer_ok and fields_ok) else "fail",
                        "response": answer_data
                    }
                    
                    if not fields_ok:
                        self.results["recommendations"].append(
                            "Answer endpoint missing required fields"
                        )
                    
                    return answer_ok and fields_ok
            except Exception as e:
                logger.error(f"Answer endpoint check failed: {e}")
                self.results["checks"]["answer_endpoint"] = {"status": "fail", "error": str(e)}
                return False

    async def validate_stream_endpoint(self) -> bool:
        """Test /answer/stream endpoint for correct event sequence"""
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "query": "Tell me about ASTRA",
                    "stream": True
                }
                async with session.post(
                    f"{self.base_url}/answer/stream",
                    json=payload
                ) as resp:
                    if resp.status != 200:
                        return False
                        
                    expected_types = {"start", "content", "citation", "end"}
                    seen_types = set()
                    
                    async for line in resp.content:
                        if line:
                            try:
                                if line.startswith(b"data: "):
                                    data = json.loads(line[6:].decode('utf-8'))
                                    if "type" in data:
                                        seen_types.add(data["type"])
                            except Exception as e:
                                logger.error(f"Stream parsing error: {e}")
                                
                    stream_ok = expected_types.issubset(seen_types)
                    self.results["checks"]["stream_endpoint"] = {
                        "status": "pass" if stream_ok else "fail",
                        "events_seen": list(seen_types)
                    }
                    
                    if not stream_ok:
                        self.results["recommendations"].append(
                            "Stream endpoint missing required event types"
                        )
                    
                    return stream_ok
            except Exception as e:
                logger.error(f"Stream endpoint check failed: {e}")
                self.results["checks"]["stream_endpoint"] = {"status": "fail", "error": str(e)}
                return False

    async def run_load_test(self) -> bool:
        """Execute load tests using Locust"""
        try:
            # Basic health and performance test
            cmd = [
                "locust",
                "-f", "locustfile.py",
                "--headless",
                "-u", "50",  # 50 users
                "-r", "10",  # Spawn rate
                "--run-time", "60s",
                "--host", self.base_url
            ]
            
            logger.info("Starting load test...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            # Parse Locust output for metrics
            success = process.returncode == 0
            self.results["checks"]["load_test"] = {
                "status": "pass" if success else "fail",
                "output": stdout,
                "errors": stderr if stderr else None
            }
            
            # Circuit breaker test
            logger.info("Testing circuit breakers...")
            env = {"CIRCUIT_BREAKER_TEST": "true"}
            cmd = [
                "locust",
                "-f", "locustfile.py",
                "--headless",
                "-u", "20",
                "-r", "5",
                "--run-time", "30s",
                "--host", self.base_url
            ]
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            cb_success = process.returncode == 0
            self.results["checks"]["circuit_breaker_test"] = {
                "status": "pass" if cb_success else "fail",
                "output": stdout,
                "errors": stderr if stderr else None
            }
            
            return success and cb_success
            
        except Exception as e:
            logger.error(f"Load test execution failed: {e}")
            self.results["checks"]["load_test"] = {"status": "fail", "error": str(e)}
            return False

    async def check_graceful_shutdown(self) -> bool:
        """Validate graceful shutdown behavior"""
        async with aiohttp.ClientSession() as session:
            try:
                # Start drain
                start_time = time.time()
                async with session.post(f"{self.base_url}/drain") as resp:
                    drain_ok = resp.status == 200
                    initial_data = await resp.json()
                
                # Monitor drain progress
                max_wait = 10  # 10 second SLO
                drained = False
                
                while time.time() - start_time < max_wait:
                    async with session.get(f"{self.base_url}/health/full") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            queue_depth = data.get("metrics", {}).get("queue_depth", 0)
                            
                            if queue_depth == 0:
                                drained = True
                                break
                    await asyncio.sleep(0.5)
                
                drain_time = time.time() - start_time
                shutdown_ok = drained and drain_time <= max_wait
                
                self.results["checks"]["graceful_shutdown"] = {
                    "status": "pass" if shutdown_ok else "fail",
                    "drain_time_seconds": drain_time,
                    "initial_queue": initial_data.get("queue_depth", 0)
                }
                
                if not shutdown_ok:
                    self.results["recommendations"].append(
                        f"Graceful shutdown took {drain_time:.1f}s (SLO: {max_wait}s)"
                    )
                
                return shutdown_ok
                
            except Exception as e:
                logger.error(f"Graceful shutdown check failed: {e}")
                self.results["checks"]["graceful_shutdown"] = {"status": "fail", "error": str(e)}
                return False

    def generate_report(self) -> str:
        """Generate markdown report of test results"""
        lines = [
            "# ASTRA Go-Live Validation Report",
            f"Generated: {self.results['timestamp']}",
            "",
            "## Health Check Status",
        ]
        
        # Health checks
        for check, result in self.results["checks"].items():
            status = "✅" if result["status"] == "pass" else "❌"
            lines.append(f"- {check}: {status}")
        
        # SLOs
        if self.results.get("slos"):
            lines.extend([
                "",
                "## SLO Compliance",
            ])
            for slo, value in self.results["slos"].items():
                lines.append(f"- {slo}: {value}")
        
        # Recommendations
        if self.results["recommendations"]:
            lines.extend([
                "",
                "## Recommendations",
            ])
            for rec in self.results["recommendations"]:
                lines.append(f"- {rec}")
        
        return "\n".join(lines)

    async def run_all_checks(self) -> bool:
        """Execute all pre-deployment validation checks"""
        logger.info("Starting pre-deployment validation...")
        
        checks = [
            ("Health Endpoints", self.check_health_endpoints()),
            ("Answer Endpoint", self.validate_answer_endpoint()),
            ("Stream Endpoint", self.validate_stream_endpoint()),
            ("Load Tests", self.run_load_test()),
            ("Graceful Shutdown", self.check_graceful_shutdown())
        ]
        
        all_passed = True
        for name, check in checks:
            logger.info(f"Running {name}...")
            try:
                passed = await check
                all_passed = all_passed and passed
                logger.info(f"{name}: {'PASS' if passed else 'FAIL'}")
            except Exception as e:
                logger.error(f"{name} failed with error: {e}")
                all_passed = False
        
        # Generate report
        report = self.generate_report()
        report_path = "go_live_validation_report.md"
        with open(report_path, "w") as f:
            f.write(report)
        
        logger.info(f"Validation report written to {report_path}")
        return all_passed

async def main():
    validator = GoLiveValidator()
    success = await validator.run_all_checks()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())