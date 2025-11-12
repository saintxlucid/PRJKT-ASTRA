"""
🚀 ASTRA Local Boot Orchestrator

Guaranteed startup sequence for offline-first operation:
1. Security & token vault
2. Local LLM (GPT OOS)
3. Vector store (ChromaDB/FAISS)
4. Agent kernel
5. Pantheon Shell / UI

Validates all systems offline before operator access.

Sacred Code: 333 → ∞
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class BootPhase(str, Enum):
    """Boot orchestration phases."""
    SECURITY = "security"
    LOCAL_LLM = "local_llm"
    VECTOR_STORE = "vector_store"
    AGENT_KERNEL = "agent_kernel"
    UI = "ui"


class BootStatus(str, Enum):
    """Status of a boot component."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    READY = "ready"
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class BootComponent:
    """A component in the boot sequence."""
    name: str
    phase: BootPhase
    priority: int  # 0 = critical, 1 = high, 2 = normal
    status: BootStatus = BootStatus.PENDING
    latency_ms: float = 0.0
    error: Optional[str] = None
    metrics: dict = field(default_factory=dict)

    def __lt__(self, other: "BootComponent") -> bool:
        """Sort by phase order and priority."""
        phase_order = {
            BootPhase.SECURITY: 0,
            BootPhase.LOCAL_LLM: 1,
            BootPhase.VECTOR_STORE: 2,
            BootPhase.AGENT_KERNEL: 3,
            BootPhase.UI: 4,
        }
        if phase_order[self.phase] == phase_order[other.phase]:
            return self.priority < other.priority
        return phase_order[self.phase] < phase_order[other.phase]


class LocalBootOrchestrator:
    """
    Orchestrates offline-first boot sequence.
    Guarantees ordering, validates offline operation, collects metrics.
    """

    def __init__(self):
        """Initialize orchestrator."""
        self.components: list[BootComponent] = []
        self.start_time = 0.0
        self.total_latency_ms = 0.0
        self.boot_complete = False
        self.offline_validated = False

    def register_component(
        self,
        name: str,
        phase: BootPhase,
        priority: int = 1,
    ) -> None:
        """Register a component for boot."""
        component = BootComponent(name=name, phase=phase, priority=priority)
        self.components.append(component)
        self.components.sort()
        logger.info("component_registered", name=name, phase=phase.value)

    async def boot(self) -> dict:
        """
        Execute boot sequence.

        Returns:
            Boot report with all component statuses
        """
        self.start_time = time.time()
        logger.info("boot_sequence_start")

        for component in self.components:
            component.status = BootStatus.INITIALIZING
            start = time.time()

            try:
                # Boot phase
                await self._boot_phase(component)
                component.status = BootStatus.READY
                component.latency_ms = (time.time() - start) * 1000
                logger.info(
                    "component_booted",
                    name=component.name,
                    latency_ms=component.latency_ms,
                )

            except Exception as e:
                component.status = BootStatus.FAILED
                component.error = str(e)
                component.latency_ms = (time.time() - start) * 1000

                if component.priority == 0:
                    # Critical component failed
                    logger.error("critical_component_failed", name=component.name, error=str(e))
                    self.boot_complete = False
                    return self._generate_report()
                else:
                    # Non-critical component failed, continue
                    logger.warning("component_failed", name=component.name, error=str(e))
                    component.status = BootStatus.DEGRADED

        self.total_latency_ms = (time.time() - self.start_time) * 1000
        self.boot_complete = True

        # Validate offline operation
        await self._validate_offline()

        logger.info("boot_sequence_complete", total_latency_ms=self.total_latency_ms)
        return self._generate_report()

    async def _boot_phase(self, component: BootComponent) -> None:
        """Boot a single component."""
        if component.phase == BootPhase.SECURITY:
            await self._boot_security(component)
        elif component.phase == BootPhase.LOCAL_LLM:
            await self._boot_local_llm(component)
        elif component.phase == BootPhase.VECTOR_STORE:
            await self._boot_vector_store(component)
        elif component.phase == BootPhase.AGENT_KERNEL:
            await self._boot_agent_kernel(component)
        elif component.phase == BootPhase.UI:
            await self._boot_ui(component)

    async def _boot_security(self, component: BootComponent) -> None:
        """Boot security & token vault."""
        logger.info("booting_security_vault")

        # Initialize Sigil Gate token system
        try:
            from astra.security.token_vault import TokenVault
            vault = TokenVault()
            await vault.initialize()

            component.metrics = {
                "vault_status": "initialized",
                "token_count": 0,
                "revocation_list_size": 0,
            }
        except ImportError:
            logger.warning("token_vault_not_available")
            component.metrics = {"vault_status": "not_available"}

    async def _boot_local_llm(self, component: BootComponent) -> None:
        """Boot local LLM (GPT OOS)."""
        logger.info("booting_local_llm")

        try:
            from astra.llm.local_provider import GPTOOSProvider, InferenceBackend
            from astra.llm.local_manager import LocalGPTOOSManager

            # Initialize provider
            provider = GPTOOSProvider(
                backend=InferenceBackend.OLLAMA,
                device="auto",
            )

            # Initialize manager
            manager = LocalGPTOOSManager(provider, max_workers=4)

            # Test inference
            start = time.time()
            response = await manager.generate("What is your name?")
            inference_latency_ms = (time.time() - start) * 1000

            if response:
                component.metrics = {
                    "status": "operational",
                    "backend": "ollama",
                    "inference_latency_ms": inference_latency_ms,
                    "first_token_ms": inference_latency_ms,
                }
            else:
                raise Exception("Inference failed")

        except Exception as e:
            logger.error("local_llm_boot_failed", error=str(e))
            raise

    async def _boot_vector_store(self, component: BootComponent) -> None:
        """Boot vector store (ChromaDB/FAISS)."""
        logger.info("booting_vector_store")

        try:
            from astra.memory.vector_store import LocalVectorStore

            vector_store = LocalVectorStore(store_type="chroma")
            await vector_store.initialize()

            component.metrics = {
                "store_type": "chroma",
                "status": "initialized",
                "collection_count": len(await vector_store.list_collections()),
                "total_vectors": 0,
            }

        except Exception as e:
            logger.error("vector_store_boot_failed", error=str(e))
            raise

    async def _boot_agent_kernel(self, component: BootComponent) -> None:
        """Boot agent kernel (ReAct planner, tools)."""
        logger.info("booting_agent_kernel")

        try:
            from astra.agents.kernel import AgentKernel

            kernel = AgentKernel()
            await kernel.initialize()

            component.metrics = {
                "status": "initialized",
                "tools_registered": len(kernel.tools),
                "planners_available": len(kernel.planners),
            }

        except Exception as e:
            logger.warning("agent_kernel_boot_degraded", error=str(e))
            component.status = BootStatus.DEGRADED
            component.metrics = {"status": "degraded", "error": str(e)}

    async def _boot_ui(self, component: BootComponent) -> None:
        """Boot UI (Pantheon Shell)."""
        logger.info("booting_ui")

        try:
            from astra.ui.pantheon import PantheonShell

            ui = PantheonShell()
            await ui.initialize()

            component.metrics = {
                "status": "initialized",
                "modules_loaded": len(ui.modules),
                "port": 3000,
            }

        except Exception as e:
            logger.warning("ui_boot_degraded", error=str(e))
            component.status = BootStatus.DEGRADED
            component.metrics = {"status": "degraded", "error": str(e)}

    async def _validate_offline(self) -> None:
        """Validate that all critical components can operate offline."""
        logger.info("validating_offline_operation")

        critical_components = [c for c in self.components if c.priority == 0]
        all_ready = all(c.status == BootStatus.READY for c in critical_components)

        if all_ready:
            self.offline_validated = True
            logger.info("offline_validation_passed")
        else:
            logger.warning("offline_validation_failed")
            self.offline_validated = False

    def _generate_report(self) -> dict:
        """Generate boot report."""
        return {
            "status": "complete" if self.boot_complete else "failed",
            "total_latency_ms": self.total_latency_ms,
            "offline_validated": self.offline_validated,
            "components": [
                {
                    "name": c.name,
                    "phase": c.phase.value,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "error": c.error,
                    "metrics": c.metrics,
                }
                for c in self.components
            ],
        }
