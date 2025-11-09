"""GGUF adapter manifest management."""

import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class AdapterConfig:
    """Configuration for a LoRA adapter."""
    path: str
    alpha: float = 0.7

    @classmethod
    def from_dict(cls, data: Dict) -> "AdapterConfig":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            alpha=data.get("alpha", 0.7)
        )

class AdapterManifest:
    """Manager for LoRA adapter manifests."""
    
    def __init__(self, manifest_path: str):
        """Initialize from manifest file.
        
        Args:
            manifest_path: Path to manifest.json
        """
        self.path = Path(manifest_path)
        self.adapters: Dict[str, AdapterConfig] = {}
        if self.path.exists():
            self.load()
            
    def load(self):
        """Load manifest from disk."""
        with open(self.path) as f:
            data = json.load(f)
            
        self.adapters = {
            name: AdapterConfig.from_dict(cfg)
            for name, cfg in data.items()
        }
        
    def save(self):
        """Save manifest to disk."""
        data = {
            name: {"path": cfg.path, "alpha": cfg.alpha}
            for name, cfg in self.adapters.items()
        }
        
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
            
    def add_adapter(
        self,
        name: str,
        path: str,
        alpha: Optional[float] = None
    ):
        """Add adapter to manifest.
        
        Args:
            name: Adapter name
            path: Path to adapter file
            alpha: Optional merge scale
        """
        if alpha is None:
            # Use standard alpha values
            alpha = {
                "planner": 0.8,
                "tooluse": 0.7, 
                "safety": 0.6
            }.get(name, 0.7)
            
        self.adapters[name] = AdapterConfig(path=path, alpha=alpha)
        self.save()
        
    def remove_adapter(self, name: str):
        """Remove adapter from manifest.
        
        Args:
            name: Adapter name to remove
        """
        if name in self.adapters:
            del self.adapters[name]
            self.save()
            
    def get_merge_order(self) -> Dict[str, AdapterConfig]:
        """Get adapters in correct merge order.
        
        Returns:
            Ordered adapter configs
        """
        # Standard merge order
        order = ["planner", "tooluse", "safety"]
        
        ordered = {}
        for name in order:
            if name in self.adapters:
                ordered[name] = self.adapters[name]
                
        # Add any remaining adapters
        for name, cfg in self.adapters.items():
            if name not in ordered:
                ordered[name] = cfg
                
        return ordered