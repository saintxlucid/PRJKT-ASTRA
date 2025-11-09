# src/astra/core/initialization.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("astra.initialization")
logger.setLevel(logging.INFO)

from ..memory_engine import MemoryEngine
from ..identity_engine import IdentityEngine
from ..neural.engine import NeuralEngine
from ..neural.model_bridge import ModelBridge
from ..neural.inference_queue import InferenceQueue
from ..neural.adapter_manager import AdapterManager

class CoreSystemsInitializer:
    """
    Bootstraps ASTRA core subsystems:
      - MemoryEngine
      - IdentityEngine (persona anchor)
      - NeuralEngine (soul runtime / model manager)
      - Services (placeholders for future: ingestion, adapters, router)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.memory: MemoryEngine | None = None
        self.identity: IdentityEngine | None = None
        self.neural: NeuralEngine | None = None
        self.model_bridge: ModelBridge | None = None
        self.inference_queue: InferenceQueue | None = None
        self.adapter_manager: AdapterManager | None = None
        self.services = {}
        self._status = {"initialized": False, "components": {}}

    async def init_memory(self):
        logger.info("Initializing MemoryEngine...")
        self.memory = MemoryEngine(self.config.get("memory", {}))
        await self.memory.connect()
        self._status["components"]["memory"] = {"status": "ready", "details": self.memory.info()}

    async def init_identity(self):
        logger.info("Initializing IdentityEngine...")
        self.identity = IdentityEngine(self.config.get("identity", {}))
        await self.identity.load()
        self._status["components"]["identity"] = {"status": "ready", "anchor": self.identity.anchor_id()}

    async def init_neural(self):
        logger.info("Initializing Neural Systems...")
        
        # Initialize base neural engine
        self.neural = NeuralEngine(self.config.get("neural", {}))
        await self.neural.start()
        self._status["components"]["neural"] = {"status": "ready", "details": self.neural.info()}
        
        # Initialize model bridge 
        self.model_bridge = ModelBridge(
            endpoint=self.config.get("model_endpoint", "http://127.0.0.1:8001"),
            cli_fallback_cmd=self.config.get("model_cli_cmd", None),
        )
        # Health check
        health = await self.model_bridge.health()
        if not health.get("ok"):
            logger.warning("Model bridge health check failed: %s", health)
        
        # Initialize inference queue
        self.inference_queue = InferenceQueue(
            self.model_bridge,
            concurrency=self.config.get("inference_concurrency", 2)
        )
        await self.inference_queue.start()
        
        # Initialize adapter manager
        self.adapter_manager = AdapterManager()
        
        self._status["components"]["model_bridge"] = {"status": "ready", "health": health}
        self._status["components"]["inference_queue"] = {"status": "ready", "concurrency": self.inference_queue.concurrency}
        self._status["components"]["adapter_manager"] = {"status": "ready"}

    async def init_services(self):
        logger.info("Initializing auxiliary services (placeholders)...")
        # Register service placeholders — ingestion, adapter manager, router, etc.
        self.services["ingest"] = {"status": "uninitialized"}
        self.services["adapter_manager"] = {"status": "uninitialized"}
        self._status["components"]["services"] = {"status": "ready", "names": list(self.services.keys())}

    async def start(self):
        logger.info("Starting full core initialization sequence...")
        try:
            await self.init_memory()
            await self.init_identity()
            await self.init_neural()
            await self.init_services()
            self._status["initialized"] = True
            logger.info("Core initialization complete.")
        except Exception as e:
            logger.exception("Initialization failed: %s", e)
            self._status["error"] = str(e)
            self._status["initialized"] = False
        return self._status

    def status(self):
        return self._status

    async def stop(self):
        """
        Orderly teardown of subsystems (idempotent).
        Stop order is the reverse of startup: services -> neural -> identity -> memory.
        Each stop is best-effort; failures are logged but do not crash shutdown.
        """
        if getattr(self, "_stopping", False):
            return self._status
        self._stopping = True
        try:
            # 1) services (including inference queue and adapters)
            try:
                if self.inference_queue:
                    await self.inference_queue.stop()
                if self.adapter_manager and hasattr(self.adapter_manager, "stop"):
                    await self.adapter_manager.stop()
                for service_name, service in self.services.items():
                    try:
                        if hasattr(service, "stop"):
                            await service.stop()
                    except Exception as e:
                        logger.exception("Stopping service %s failed: %s", service_name, e)
            except Exception as e:
                logger.exception("Stopping services failed: %s", e)

            # 2) model bridge and neural
            try:
                if self.model_bridge:
                    await self.model_bridge.aclose()
                if self.neural:
                    await self.neural.stop()
            except Exception as e:
                logger.exception("Stopping neural systems failed: %s", e)

            # 3) identity
            try:
                if self.identity and hasattr(self.identity, "stop"):
                    await self.identity.stop()
            except Exception as e:
                logger.exception("Stopping identity failed: %s", e)

            # 4) memory (persist/flush last)
            try:
                if self.memory and hasattr(self.memory, "close"):
                    await self.memory.close()
            except Exception as e:
                logger.exception("Closing memory failed: %s", e)

            self._status["initialized"] = False
            self._status["components"]["shutdown"] = {"status": "complete"}
        finally:
            self._stopping = False
        return self._status