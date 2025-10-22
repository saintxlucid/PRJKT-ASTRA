"""
Configuration settings for reranker components.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class RerankerConfig:
    """Reranker configuration settings."""
    
    # Model settings
    model_name: str = "BAAI/bge-reranker-base"
    max_length: int = 512
    batch_size: int = 8
    use_fp16: bool = True
    
    # Diversity settings
    section_bonus: float = 0.1  # Bonus for distinct sections
    heading_bonus: float = 0.05  # Bonus for distinct headings
    
    # Cache settings
    cache_dir: str = "data/cache/reranker"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "model": {
                "name": self.model_name,
                "max_length": self.max_length,
                "batch_size": self.batch_size,
                "use_fp16": self.use_fp16
            },
            "diversity": {
                "section_bonus": self.section_bonus,
                "heading_bonus": self.heading_bonus
            },
            "cache": {
                "dir": self.cache_dir
            }
        }
        
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'RerankerConfig':
        """Create config from dictionary."""
        model_cfg = config.get("model", {})
        diversity_cfg = config.get("diversity", {})
        cache_cfg = config.get("cache", {})
        
        return cls(
            model_name=model_cfg.get("name", cls.model_name),
            max_length=model_cfg.get("max_length", cls.max_length),
            batch_size=model_cfg.get("batch_size", cls.batch_size),
            use_fp16=model_cfg.get("use_fp16", cls.use_fp16),
            section_bonus=diversity_cfg.get("section_bonus", cls.section_bonus),
            heading_bonus=diversity_cfg.get("heading_bonus", cls.heading_bonus),
            cache_dir=cache_cfg.get("dir", cls.cache_dir)
        )
        
# Performance profiles
DEFAULT_CONFIGS = {
    "fast": RerankerConfig(
        max_length=256,
        batch_size=16,
        use_fp16=True,
        section_bonus=0.05,
        heading_bonus=0.02
    ),
    
    "balanced": RerankerConfig(
        max_length=512,
        batch_size=8,
        use_fp16=True,
        section_bonus=0.1,
        heading_bonus=0.05
    ),
    
    "quality": RerankerConfig(
        max_length=768,
        batch_size=4,
        use_fp16=False,
        section_bonus=0.15,
        heading_bonus=0.08
    )
}