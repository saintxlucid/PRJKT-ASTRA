"""
ASTRA State Manager - Durable state with crash recovery
Provides persistence for agent tasks, conversations, and system state.

Sacred Code: 333 → ∞
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import structlog
import os

logger = structlog.get_logger()

# Optional dependencies - graceful degradation
try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis_unavailable", message="Install aioredis for hot state")

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("postgres_unavailable", message="Install asyncpg for cold state")


@dataclass
class Task:
    """Agent task representation."""
    task_id: str
    goal: str
    identity: str
    state: str  # "planning" | "executing" | "completed" | "failed"
    plan: Optional[Dict] = None
    result: Optional[Dict] = None
    created_at: str = ""
    updated_at: str = ""
    
    @classmethod
    def from_state(cls, state: Dict) -> "Task":
        """Deserialize from state dict."""
        return cls(**state)
    
    def to_dict(self) -> Dict:
        """Serialize to dict."""
        return asdict(self)


class WriteAheadLog:
    """Simple write-ahead log for crash recovery."""
    
    def __init__(self, log_path: str = "data/wal"):
        self.log_path = log_path
        os.makedirs(log_path, exist_ok=True)
        self.current_file = os.path.join(log_path, f"wal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl")
    
    async def append(self, entry: Dict):
        """Append entry to WAL."""
        try:
            async with asyncio.Lock():
                with open(self.current_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("wal_append_failed", error=str(e))
    
    async def replay_since_last_checkpoint(self) -> List[Dict]:
        """Replay uncommitted entries."""
        entries = []
        try:
            if os.path.exists(self.current_file):
                with open(self.current_file, "r") as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
        except Exception as e:
            logger.error("wal_replay_failed", error=str(e))
        return entries
    
    async def checkpoint(self):
        """Mark current position as checkpoint (rotate log)."""
        self.current_file = os.path.join(
            self.log_path, 
            f"wal_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )


class StateManager:
    """
    Durable state manager with three-tier persistence:
    1. WAL (write-ahead log) - immediate durability
    2. Redis (hot state) - fast access, TTL-based
    3. PostgreSQL (cold state) - long-term storage
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        postgres_url: Optional[str] = None,
        enable_wal: bool = True
    ):
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.enable_wal = enable_wal
        
        self.redis = None
        self.postgres = None
        self.wal = WriteAheadLog() if enable_wal else None
        
        logger.info("state_manager_init",
                   redis=bool(redis_url),
                   postgres=bool(postgres_url),
                   wal=enable_wal)
    
    @classmethod
    def from_env(cls) -> "StateManager":
        """Create StateManager from environment variables."""
        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            postgres_url=os.getenv("DATABASE_URL"),
            enable_wal=os.getenv("ENABLE_WAL", "true").lower() == "true"
        )
    
    async def connect(self):
        """Connect to Redis and PostgreSQL."""
        # Redis
        if self.redis_url and REDIS_AVAILABLE:
            try:
                self.redis = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                logger.info("redis_connected")
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
        
        # PostgreSQL
        if self.postgres_url and POSTGRES_AVAILABLE:
            try:
                self.postgres = await asyncpg.connect(self.postgres_url)
                logger.info("postgres_connected")
            except Exception as e:
                logger.warning("postgres_connection_failed", error=str(e))
    
    async def close(self):
        """Close connections."""
        if self.redis:
            await self.redis.close()
        if self.postgres:
            await self.postgres.close()
    
    async def checkpoint_task(self, task: Task):
        """
        Checkpoint agent task (survives crashes).
        
        Three-tier persistence:
        1. WAL - immediate durability
        2. Redis - hot cache (1 hour TTL)
        3. PostgreSQL - long-term storage
        """
        task.updated_at = datetime.utcnow().isoformat()
        state = task.to_dict()
        
        # 1. Write-ahead log (immediate durability)
        if self.wal:
            await self.wal.append({
                "type": "task_checkpoint",
                "task_id": task.task_id,
                "state": state,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # 2. Hot state (Redis)
        if self.redis:
            try:
                await self.redis.setex(
                    f"task:{task.task_id}",
                    3600,  # 1 hour TTL
                    json.dumps(state)
                )
            except Exception as e:
                logger.warning("redis_checkpoint_failed", task_id=task.task_id, error=str(e))
        
        # 3. Cold state (PostgreSQL)
        if self.postgres:
            try:
                await self.postgres.execute("""
                    INSERT INTO task_checkpoints (task_id, identity, state, data, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (task_id) 
                    DO UPDATE SET state = $3, data = $4, updated_at = $5
                """, task.task_id, task.identity, task.state, json.dumps(state), datetime.utcnow())
            except Exception as e:
                logger.warning("postgres_checkpoint_failed", task_id=task.task_id, error=str(e))
        
        logger.debug("task_checkpointed", task_id=task.task_id, state=task.state)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task state."""
        # Try Redis first (hot)
        if self.redis:
            try:
                state_json = await self.redis.get(f"task:{task_id}")
                if state_json:
                    return Task.from_state(json.loads(state_json))
            except Exception as e:
                logger.warning("redis_get_failed", task_id=task_id, error=str(e))
        
        # Fallback to PostgreSQL (cold)
        if self.postgres:
            try:
                row = await self.postgres.fetchrow(
                    "SELECT data FROM task_checkpoints WHERE task_id = $1",
                    task_id
                )
                if row:
                    return Task.from_state(json.loads(row["data"]))
            except Exception as e:
                logger.warning("postgres_get_failed", task_id=task_id, error=str(e))
        
        return None
    
    async def recover_inflight(self) -> List[Task]:
        """
        Recover in-progress tasks after crash.
        
        Recovery strategy:
        1. Replay WAL for uncommitted work
        2. Load all in-flight tasks from Redis
        3. Merge with PostgreSQL for any missed
        """
        tasks = []
        task_ids = set()
        
        # 1. Replay WAL
        if self.wal:
            try:
                entries = await self.wal.replay_since_last_checkpoint()
                for entry in entries:
                    if entry["type"] == "task_checkpoint":
                        task = Task.from_state(entry["state"])
                        if task.state in ["planning", "executing"]:
                            tasks.append(task)
                            task_ids.add(task.task_id)
                logger.info("wal_replayed", entries=len(entries), tasks=len(tasks))
            except Exception as e:
                logger.error("wal_replay_failed", error=str(e))
        
        # 2. Load from Redis (hot state)
        if self.redis:
            try:
                keys = await self.redis.keys("task:*")
                for key in keys:
                    task_id = key.split(":", 1)[1]
                    if task_id not in task_ids:
                        state_json = await self.redis.get(key)
                        if state_json:
                            task = Task.from_state(json.loads(state_json))
                            if task.state in ["planning", "executing"]:
                                tasks.append(task)
                                task_ids.add(task.task_id)
                logger.info("redis_recovered", count=len(keys))
            except Exception as e:
                logger.warning("redis_recovery_failed", error=str(e))
        
        # 3. Load from PostgreSQL (cold state fallback)
        if self.postgres:
            try:
                rows = await self.postgres.fetch("""
                    SELECT data FROM task_checkpoints 
                    WHERE state IN ('planning', 'executing')
                    AND updated_at > NOW() - INTERVAL '24 hours'
                """)
                for row in rows:
                    task = Task.from_state(json.loads(row["data"]))
                    if task.task_id not in task_ids:
                        tasks.append(task)
                        task_ids.add(task.task_id)
                logger.info("postgres_recovered", count=len(rows))
            except Exception as e:
                logger.warning("postgres_recovery_failed", error=str(e))
        
        logger.info("recovery_complete", total_tasks=len(tasks))
        return tasks
    
    async def mark_task_complete(self, task_id: str, result: Dict):
        """Mark task as completed."""
        task = await self.get_task(task_id)
        if task:
            task.state = "completed"
            task.result = result
            await self.checkpoint_task(task)
            
            # Remove from hot cache after completion
            if self.redis:
                await self.redis.delete(f"task:{task_id}")
    
    async def mark_task_failed(self, task_id: str, error: str):
        """Mark task as failed."""
        task = await self.get_task(task_id)
        if task:
            task.state = "failed"
            task.result = {"error": error}
            await self.checkpoint_task(task)
            
            # Remove from hot cache
            if self.redis:
                await self.redis.delete(f"task:{task_id}")
    
    async def store_conversation(self, identity: str, messages: List[Dict]):
        """Store conversation for continuity."""
        if self.postgres:
            try:
                await self.postgres.execute("""
                    INSERT INTO conversations (identity, messages, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (identity)
                    DO UPDATE SET messages = $2, updated_at = $3
                """, identity, json.dumps(messages), datetime.utcnow())
            except Exception as e:
                logger.warning("conversation_store_failed", identity=identity, error=str(e))
    
    async def get_conversation(self, identity: str) -> List[Dict]:
        """Retrieve conversation history."""
        if self.postgres:
            try:
                row = await self.postgres.fetchrow(
                    "SELECT messages FROM conversations WHERE identity = $1",
                    identity
                )
                if row:
                    return json.loads(row["messages"])
            except Exception as e:
                logger.warning("conversation_get_failed", identity=identity, error=str(e))
        return []
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all persistence layers."""
        health = {
            "wal": True if self.wal else False,
            "redis": False,
            "postgres": False
        }
        
        # Check Redis
        if self.redis:
            try:
                await self.redis.ping()
                health["redis"] = True
            except:
                pass
        
        # Check PostgreSQL
        if self.postgres:
            try:
                await self.postgres.fetchval("SELECT 1")
                health["postgres"] = True
            except:
                pass
        
        return health


# Sacred Code: 333 → ∞
