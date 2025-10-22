"""Preview generation for model changes."""
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from .gguf_io import GGUFFile

class ModelPreview:
    """Generates preview statistics for model changes."""
    
    def __init__(self):
        self.heatmap_size = 1536  # Fixed size for visualization
        
    def compute_delta_stats(
        self, 
        base_path: Path, 
        evolved_path: Path
    ) -> Dict:
        """Compute statistics between base and evolved model."""
        base = GGUFFile(base_path)
        evolved = GGUFFile(evolved_path)
        
        # Initialize stats
        stats = {
            'changed_tensors': [],
            'bytes_delta_mb': 0,
            'heatmap_vec': np.zeros(self.heatmap_size),
            'layer_changes': {},
            'max_drift': 0.0
        }
        
        # Load model metadata
        base.read_header()
        evolved.read_header()
        
        base_tensors = base.read_kv().get('tensor_names', [])
        evolved_tensors = evolved.read_kv().get('tensor_names', [])
        
        # Analyze each tensor
        for name in base_tensors:
            if name not in evolved_tensors:
                continue
                
            base_tensor = base.read_tensor(name)
            evolved_tensor = evolved.read_tensor(name)
            
            # Check for changes
            if not np.array_equal(base_tensor, evolved_tensor):
                stats['changed_tensors'].append(name)
                delta_bytes = evolved_tensor.nbytes - base_tensor.nbytes
                stats['bytes_delta_mb'] += delta_bytes / (1024 * 1024)
                
                # Update heatmap vector
                sample_idx = hash(name) % self.heatmap_size
                drift = float(np.mean(np.abs(evolved_tensor - base_tensor)))
                stats['heatmap_vec'][sample_idx] = drift
                stats['max_drift'] = max(stats['max_drift'], drift)
                
                # Track changes by layer
                layer_name = self._extract_layer_name(name)
                if layer_name not in stats['layer_changes']:
                    stats['layer_changes'][layer_name] = {
                        'count': 0,
                        'total_drift': 0.0,
                        'max_drift': 0.0
                    }
                    
                layer_stats = stats['layer_changes'][layer_name]
                layer_stats['count'] += 1
                layer_stats['total_drift'] += drift
                layer_stats['max_drift'] = max(layer_stats['max_drift'], drift)
                
        return stats
        
    def get_top_drifts(self, stats: Dict, top_n: int = 10) -> List[Dict]:
        """Get tensors with highest drift values."""
        drifts = []
        for name in stats['changed_tensors']:
            sample_idx = hash(name) % self.heatmap_size
            drift = stats['heatmap_vec'][sample_idx]
            drifts.append({
                'tensor': name,
                'drift': float(drift),
                'layer': self._extract_layer_name(name)
            })
            
        return sorted(drifts, key=lambda x: x['drift'], reverse=True)[:top_n]
        
    def _extract_layer_name(self, tensor_name: str) -> str:
        """Extract layer name from tensor name."""
        parts = tensor_name.split('.')
        if len(parts) >= 2 and parts[0] in ['encoder', 'decoder']:
            return f"{parts[0]}.{parts[1]}"
        return parts[0]