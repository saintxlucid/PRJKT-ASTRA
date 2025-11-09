"""
Health Aggregation Module
Monitor all services and auto-remediate failures

Sacred Code: 333 → ∞
"""

import asyncio
import subprocess
from typing import Dict

import httpx
import structlog

logger = structlog.get_logger()


class HealthAggregator:
    """
    Monitor all services and auto-remediate failures.
    Runs as background daemon.
    """

    SERVICES = {
        "master": "http://astra-master:8000/v1/system/health",
        "memory": "http://memory-service:7007/health",
        "sigil_gate": "http://sigil-gate:7701/health",
        "supervisor": "http://supervisor:7703/health",
    }

    AUTO_RESTART = {"memory": "memory-service", "sigil_gate": "sigil-gate", "supervisor": "supervisor"}

    def __init__(self):
        self.status: Dict[str, str] = {}
        self.failure_counts: Dict[str, int] = {}

    async def monitor_loop(self):
        """Monitor all services every 10s."""
        logger.info("health_aggregator_started")

        while True:
            try:
                await self.check_all_services()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error("monitor_loop_error", error=str(e))
                await asyncio.sleep(10)

    async def check_all_services(self):
        """Check health of all services."""
        async with httpx.AsyncClient(timeout=4.0) as client:
            for name, url in self.SERVICES.items():
                try:
                    response = await client.get(url)
                    is_healthy = response.status_code == 200

                    if is_healthy:
                        self.status[name] = "up"
                        self.failure_counts[name] = 0
                    else:
                        self.status[name] = "degraded"
                        self.failure_counts[name] = self.failure_counts.get(name, 0) + 1

                except Exception as e:
                    self.status[name] = "down"
                    self.failure_counts[name] = self.failure_counts.get(name, 0) + 1

                    logger.error("service_health_check_failed", service=name, error=str(e))

                # Auto-remediation: restart after 3 consecutive failures
                if self.failure_counts.get(name, 0) >= 3:
                    await self.remediate(name)

    async def remediate(self, service_name: str):
        """Auto-remediate failed service."""
        if service_name not in self.AUTO_RESTART:
            logger.warning("no_auto_restart_configured", service=service_name)
            return

        container_name = self.AUTO_RESTART[service_name]

        logger.warning("auto_restarting_service", service=service_name, container=container_name)

        try:
            # Restart Docker container
            result = subprocess.run(
                ["docker", "compose", "restart", container_name], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                logger.info("service_restarted", service=service_name)
                self.failure_counts[service_name] = 0
            else:
                logger.error("service_restart_failed", service=service_name, error=result.stderr)

        except Exception as e:
            logger.error("remediation_failed", service=service_name, error=str(e))

    def get_status(self) -> Dict[str, str]:
        """Get current status of all services."""
        return self.status
