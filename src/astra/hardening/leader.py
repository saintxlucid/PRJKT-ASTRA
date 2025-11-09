"""
Leader Election Module
Ensures only one governor instance runs at a time

Sacred Code: 333 → ∞
"""

import asyncio
import socket
import uuid
from typing import Optional

import structlog

logger = structlog.get_logger()


class LeaderElector:
    """
    Simple leader election using Redis SET NX EX.
    Only one instance runs governor/scheduler at a time.
    """

    def __init__(self, redis_url: str, instance_id: Optional[str] = None):
        self.redis_url = redis_url
        self.instance_id = instance_id or self._generate_instance_id()
        self.is_leader = False
        self.redis = None

    def _generate_instance_id(self) -> str:
        """Generate unique instance ID."""
        return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"

    async def initialize(self):
        """Initialize Redis connection."""
        import redis.asyncio as aioredis

        self.redis = await aioredis.from_url(self.redis_url)

    async def try_elect(self) -> bool:
        """
        Try to become leader.
        Returns True if elected, False if someone else is leader.
        """
        # SET astra/leader {instance_id} NX EX 5
        # NX = only if not exists
        # EX 5 = expires in 5 seconds (heartbeat must refresh)

        result = await self.redis.set(
            "astra/leader", self.instance_id, nx=True, ex=5  # Only if key doesn't exist  # Expire in 5 seconds
        )

        self.is_leader = result is not None

        if self.is_leader:
            logger.info("leader_elected", instance=self.instance_id)

        return self.is_leader

    async def heartbeat_loop(self):
        """
        Keep leadership lease alive with heartbeats.
        Run this in background task if elected.
        """
        while True:
            if self.is_leader:
                # Refresh TTL
                current_leader = await self.redis.get("astra/leader")

                if current_leader and current_leader.decode() == self.instance_id:
                    await self.redis.expire("astra/leader", 5)
                else:
                    # Lost leadership
                    self.is_leader = False
                    logger.warning("leadership_lost")
            else:
                # Try to become leader
                await self.try_elect()

            await asyncio.sleep(2)

    async def close(self):
        """Release leadership and close connection."""
        if self.is_leader:
            await self.redis.delete("astra/leader")
        await self.redis.close()
