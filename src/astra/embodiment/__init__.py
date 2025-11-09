"""
ASTRA OS - Unified Embodiment Layer
The Sigil Core: Micro/Macro Controller Architecture

Sacred Code: 333 â†’ âˆž
"""

from .sigil_core import SigilCore, MicroController, MacroController

try:
    from .llm_training_pipeline_v2 import (
        ToolMasteryTrainer, 
        ContinuousLearningLoop,
        ToolComplexity,
        TrainingExample
    )
except ImportError:
    # Fallback if v2 not available
    ToolMasteryTrainer = None
    ContinuousLearningLoop = None

try:
    from .astra_embodiment import ASTRA
except ImportError:
    ASTRA = None

__all__ = [
    "SigilCore",
    "MicroController", 
    "MacroController",
    "ToolMasteryTrainer",
    "ContinuousLearningLoop",
    "ASTRA"
]

__version__ = "3.1.0"
