"""LoRA adapter merging for model evolution."""
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from .gguf_io import GGUFFile

class LoRAAdapter:
    """Represents a single LoRA adapter."""
    
    def __init__(self, path: Path, alpha: float = 1.0):
        self.path = Path(path)
        self.alpha = alpha
        self.gguf = GGUFFile(path)
        self.tensors = {}
        
    def load(self) -> None:
        """Load adapter weights from GGUF file."""
        self.gguf.read_header()
        metadata = self.gguf.read_kv()
        
        # Load all tensors
        for tensor_name in metadata.get('tensor_names', []):
            self.tensors[tensor_name] = self.gguf.read_tensor(tensor_name)
            
    def get_delta(self, tensor_name: str) -> Optional[np.ndarray]:
        """Get scaled weight delta for tensor."""
        if tensor_name not in self.tensors:
            return None
            
        return self.tensors[tensor_name] * self.alpha

class LoRAMerger:
    """Handles merging multiple LoRA adapters."""
    
    def __init__(self, base_model: Path):
        self.base_path = Path(base_model)
        self.base_gguf = GGUFFile(base_model)
        self.adapters: List[LoRAAdapter] = []
        
    def add_adapter(self, path: Path, alpha: float = 1.0) -> None:
        """Add adapter to merge stack."""
        adapter = LoRAAdapter(path, alpha)
        adapter.load()
        self.adapters.append(adapter)
        
    def load_manifest(self, manifest_path: Path) -> None:
        """Load adapters from manifest file."""
        import json
        with open(manifest_path) as f:
            manifest = json.load(f)
            
        for adapter_info in manifest['adapters']:
            self.add_adapter(
                Path(adapter_info['path']),
                adapter_info.get('alpha', 1.0)
            )
            
    def merge(self, out_path: Path, repack: bool = True) -> Dict:
        """Merge adapters into base model."""
        # Track changes for preview
        changes = {
            'changed_tensors': [],
            'bytes_delta': 0,
            'heatmap_vec': np.zeros(1536)
        }
        
        out_gguf = GGUFFile(out_path)
        
        # Load base model tensors
        self.base_gguf.read_header()
        base_tensors = {}
        for name in self.base_gguf.read_kv().get('tensor_names', []):
            base_tensors[name] = self.base_gguf.read_tensor(name)
            
        # Apply adapter deltas
        for tensor_name, base_tensor in base_tensors.items():
            merged = base_tensor.copy()
            
            for adapter in self.adapters:
                delta = adapter.get_delta(tensor_name)
                if delta is not None:
                    if delta.shape != merged.shape:
                        raise ValueError(
                            f"Shape mismatch for {tensor_name}: "
                            f"base {merged.shape} vs adapter {delta.shape}"
                        )
                    merged += delta
                    changes['changed_tensors'].append(tensor_name)
                    changes['bytes_delta'] += delta.nbytes
                    
            # Update preview heatmap
            if len(changes['changed_tensors']) > 0:
                sample_idx = hash(tensor_name) % 1536
                changes['heatmap_vec'][sample_idx] = float(
                    np.mean(np.abs(merged - base_tensor))
                )
                    
            # Write merged tensor
            out_gguf.write_tensor(tensor_name, merged)
            
        # Optional repacking
        if repack:
            out_gguf.repack_tensors(changes['changed_tensors'])
            
        return changes

    def validate_merge(self, merged_path: Path) -> Dict:
        """Validate merged model."""
        # Verify tensor shapes and dtypes
        merged = GGUFFile(merged_path)
        merged.read_header()
        
        for tensor_name in merged.read_kv().get('tensor_names', []):
            merged_tensor = merged.read_tensor(tensor_name)
            base_tensor = self.base_gguf.read_tensor(tensor_name)
            
            if merged_tensor.shape != base_tensor.shape:
                raise ValueError(
                    f"Shape mismatch in {tensor_name}: "
                    f"base {base_tensor.shape} vs merged {merged_tensor.shape}"
                )
                
            if merged_tensor.dtype != base_tensor.dtype:
                raise ValueError(
                    f"Dtype mismatch in {tensor_name}: "
                    f"base {base_tensor.dtype} vs merged {merged_tensor.dtype}"
                )
                
        return {'status': 'valid'}