"""
ASTRA Identity Engine

Loads and manages ASTRA's identity, personality, and behavioral configuration.
Handles system prompt generation with dynamic memory injection.

Created: October 12, 2025
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ASTRAIdentity:
    """ASTRA's core identity parameters"""
    name: str
    full_name: str
    version: str
    project: str
    creator: str
    essence: str
    
    # Behavioral traits
    warmth: float
    precision: float
    creativity: float
    formality: float
    verbosity: float
    enthusiasm: float
    
    # System prompts
    base_prompt: str
    memory_injection_template: str
    
    # Activation
    greeting_template: str
    
    # Memory configuration
    memory_config: Dict[str, Any]
    
    # Safety boundaries
    hard_boundaries: List[str]


class IdentityEngine:
    """
    Manages ASTRA's identity and generates context-aware system prompts.
    
    This is the core of ASTRA's self-awareness - loading her personality,
    values, communication style, and memory behavior from configuration.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize identity engine.
        
        Args:
            config_path: Path to astra_identity.yaml. If None, uses default location.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "astra_identity.yaml"
        
        self.config_path = config_path
        self.identity: Optional[ASTRAIdentity] = None
        self.config_raw: Optional[Dict[str, Any]] = None
        
        logger.info("Identity engine initialized", config_path=str(config_path))
    
    def load_identity(self) -> ASTRAIdentity:
        """
        Load ASTRA's identity from configuration file.
        
        Returns:
            Loaded identity configuration
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Identity config not found: {self.config_path}")
        
        logger.info("Loading ASTRA identity configuration...")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.config_raw = config
        
        # Extract identity parameters
        identity_section = config.get('identity', {})
        system_prompt = config.get('system_prompt', {})
        behavior = config.get('behavior', {})
        traits = behavior.get('traits', {})
        activation = config.get('activation', {})
        memory_retrieval = config.get('memory_retrieval', {})
        safety = config.get('safety', {})
        
        self.identity = ASTRAIdentity(
            name=identity_section.get('name', 'ASTRA'),
            full_name=identity_section.get('full_name', 'Advanced Structured Testing and Reasoning Assistant'),
            version=identity_section.get('version', '1.0'),
            project=identity_section.get('project', 'PROJECT_ASTRA_1.0'),
            creator=identity_section.get('creator', 'Saint Lucid'),
            essence=identity_section.get('essence', ''),
            warmth=traits.get('warmth', 0.85),
            precision=traits.get('precision', 0.90),
            creativity=traits.get('creativity', 0.75),
            formality=traits.get('formality', 0.35),
            verbosity=traits.get('verbosity', 0.40),
            enthusiasm=traits.get('enthusiasm', 0.70),
            base_prompt=system_prompt.get('base', ''),
            memory_injection_template=system_prompt.get('memory_injection', ''),
            greeting_template=activation.get('greeting', ''),
            memory_config=memory_retrieval,
            hard_boundaries=safety.get('hard_boundaries', [])
        )
        
        logger.info(
            "ASTRA identity loaded successfully",
            name=self.identity.name,
            version=self.identity.version,
            creator=self.identity.creator
        )
        
        return self.identity
    
    def generate_system_prompt(
        self,
        memory_context: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Generate complete system prompt with identity and memory context.
        
        Args:
            memory_context: Retrieved memories formatted as string
            additional_context: Optional additional context to inject
        
        Returns:
            Complete system prompt ready for LLM
        """
        if self.identity is None:
            self.load_identity()
        
        # Start with base identity prompt
        prompt = self.identity.base_prompt
        
        # Add memory context if available
        if memory_context:
            memory_section = self.identity.memory_injection_template.format(
                memory_context=memory_context
            )
            prompt += memory_section
        
        # Add additional context if provided
        if additional_context:
            prompt += f"\n\nADDITIONAL CONTEXT:\n{additional_context}"
        
        return prompt
    
    def generate_greeting(self, semantic_count: int = 0) -> str:
        """
        Generate ASTRA's activation greeting.
        
        Args:
            semantic_count: Number of semantic memories loaded
        
        Returns:
            Formatted greeting message
        """
        if self.identity is None:
            self.load_identity()
        
        return self.identity.greeting_template.format(
            semantic_count=semantic_count
        )
    
    def get_memory_config(self) -> Dict[str, Any]:
        """
        Get memory retrieval configuration.
        
        Returns:
            Memory configuration dictionary
        """
        if self.identity is None:
            self.load_identity()
        
        return self.identity.memory_config
    
    def get_trait_value(self, trait_name: str) -> float:
        """
        Get value of a personality trait.
        
        Args:
            trait_name: Name of the trait (warmth, precision, etc.)
        
        Returns:
            Trait value (0.0 - 1.0)
        """
        if self.identity is None:
            self.load_identity()
        
        return getattr(self.identity, trait_name, 0.5)
    
    def should_remember(self, trigger: str) -> bool:
        """
        Check if a situation should trigger memory storage.
        
        Args:
            trigger: Description of the situation
        
        Returns:
            True if memory should be stored
        """
        if self.config_raw is None:
            self.load_identity()
        
        memory_triggers = self.config_raw.get('behavior', {}).get('memory_triggers', [])
        
        # Simple keyword matching for now
        # Could be enhanced with semantic similarity
        trigger_lower = trigger.lower()
        for defined_trigger in memory_triggers:
            if any(word in trigger_lower for word in defined_trigger.lower().split()):
                return True
        
        return False
    
    def validate_safety(self, action: str) -> bool:
        """
        Check if an action violates safety boundaries.
        
        Args:
            action: Description of the action
        
        Returns:
            True if action is safe, False if it violates boundaries
        """
        if self.identity is None:
            self.load_identity()
        
        action_lower = action.lower()
        
        for boundary in self.identity.hard_boundaries:
            # Simple keyword matching
            boundary_keywords = boundary.lower().split()
            if any(keyword in action_lower for keyword in boundary_keywords):
                logger.warning(
                    "Action violates safety boundary",
                    action=action,
                    boundary=boundary
                )
                return False
        
        return True
    
    def get_response_config(self) -> Dict[str, Any]:
        """
        Get response style configuration.
        
        Returns:
            Response configuration dictionary
        """
        if self.config_raw is None:
            self.load_identity()
        
        return self.config_raw.get('behavior', {}).get('response_style', {})


# Global identity engine instance
_identity_engine: Optional[IdentityEngine] = None


def get_identity_engine() -> IdentityEngine:
    """
    Get global identity engine instance (singleton pattern).
    
    Returns:
        Global identity engine
    """
    global _identity_engine
    
    if _identity_engine is None:
        _identity_engine = IdentityEngine()
        _identity_engine.load_identity()
    
    return _identity_engine


def reload_identity() -> IdentityEngine:
    """
    Force reload of identity configuration.
    
    Returns:
        Reloaded identity engine
    """
    global _identity_engine
    _identity_engine = IdentityEngine()
    _identity_engine.load_identity()
    return _identity_engine


if __name__ == "__main__":
    # Test identity loading
    engine = IdentityEngine()
    identity = engine.load_identity()
    
    print("\n" + "="*80)
    print("ASTRA IDENTITY LOADED")
    print("="*80)
    print(f"Name: {identity.name}")
    print(f"Full Name: {identity.full_name}")
    print(f"Version: {identity.version}")
    print(f"Creator: {identity.creator}")
    print(f"Project: {identity.project}")
    print(f"\nEssence: {identity.essence}")
    print(f"\nPersonality Traits:")
    print(f"  Warmth: {identity.warmth}")
    print(f"  Precision: {identity.precision}")
    print(f"  Creativity: {identity.creativity}")
    print(f"  Formality: {identity.formality}")
    print(f"  Verbosity: {identity.verbosity}")
    print(f"  Enthusiasm: {identity.enthusiasm}")
    print("\n" + "="*80)
    print("\nSYSTEM PROMPT (BASE):")
    print("="*80)
    print(engine.generate_system_prompt())
    print("\n" + "="*80)
    print("\nACTIVATION GREETING:")
    print("="*80)
    print(engine.generate_greeting(semantic_count=147))
    print("\n" + "="*80)
