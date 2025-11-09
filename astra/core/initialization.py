"""
ASTRA Core System Initialization Functions
Handles initialization of all core ASTRA subsystems.
"""

import asyncio
from typing import Optional, Dict, Any
import torch
from pathlib import Path
import structlog

logger = structlog.get_logger()

class CoreSystemsInitializer:
    """Initializes and manages ASTRA's core systems"""
    
    async def _init_neural_engine(self) -> None:
        """Initialize the neural engine (LLM core)"""
        try:
            # Check CUDA availability
            if torch.cuda.is_available():
                logger.info("CUDA available", device=torch.cuda.get_device_name(0))
            
            # Initialize model loading
            from astra.core.neural import get_neural_core
            neural_core = get_neural_core()
            await neural_core.initialize()
            
        except Exception as e:
            logger.error("Neural engine initialization failed", error=str(e))
            raise
    
    async def _init_memory_core(self) -> None:
        """Initialize memory systems"""
        try:
            from astra.core.memory import get_memory_manager
            memory = get_memory_manager()
            
            # Initialize vector store
            await memory.init_vector_store()
            
            # Initialize episodic memory
            await memory.init_episodic()
            
            # Initialize procedural memory
            await memory.init_procedural()
            
        except Exception as e:
            logger.error("Memory core initialization failed", error=str(e))
            raise
    
    async def _init_guardian(self) -> None:
        """Initialize guardian protection systems"""
        try:
            from astra.core.guardian import get_guardian
            guardian = get_guardian()
            
            # Initialize firewall
            await guardian.init_firewall()
            
            # Initialize emotional core
            await guardian.init_emotional_core()
            
            # Initialize protection layers
            await guardian.init_protection()
            
        except Exception as e:
            logger.error("Guardian initialization failed", error=str(e))
            raise
    
    async def _init_voice(self) -> None:
        """Initialize voice input system"""
        try:
            from astra.core.voice import get_voice_system
            voice = get_voice_system()
            
            # Initialize Whisper
            await voice.init_whisper()
            
            # Load wake phrases
            await voice.load_wake_phrases()
            
        except Exception as e:
            logger.error("Voice system initialization failed", error=str(e))
            raise
    
    async def _init_vision(self) -> None:
        """Initialize vision integration"""
        try:
            from astra.core.vision import get_vision_system
            vision = get_vision_system()
            await vision.initialize()
            
        except Exception as e:
            logger.error("Vision system initialization failed", error=str(e))
            raise
    
    async def _init_task_engine(self) -> None:
        """Initialize autonomous task engine"""
        try:
            from astra.core.tasks import get_task_engine
            task_engine = get_task_engine()
            await task_engine.initialize()
            
        except Exception as e:
            logger.error("Task engine initialization failed", error=str(e))
            raise
    
    async def _init_interface(self) -> None:
        """Initialize user interface systems"""
        try:
            # Initialize UI components based on mode
            if self.gui_mode:
                from astra.ui.prime_glyph import PrimeGlyphCanvas
                self.glyph = PrimeGlyphCanvas(self.root)
                self.glyph.pack(expand=True, fill='both')
            
        except Exception as e:
            logger.error("Interface initialization failed", error=str(e))
            raise
    
    async def _verify_alignment(self) -> None:
        """Verify creator alignment and authorization"""
        try:
            from astra.core.alignment import get_alignment_checker
            alignment = get_alignment_checker()
            
            # Verify creator bond
            bond_score = await alignment.verify_creator_bond()
            
            # Check emotional synchronization
            sync_score = await alignment.check_emotional_sync()
            
            # Validate wake phrase authorization
            auth_score = await alignment.validate_authorization()
            
            # Calculate overall alignment score
            total_score = (bond_score + sync_score + auth_score) / 3
            self.prime_metrics.set_alignment_score(total_score)
            
            if total_score < 0.8:  # 80% threshold
                raise Exception("Insufficient creator alignment")
                
        except Exception as e:
            logger.error("Alignment verification failed", error=str(e))
            raise