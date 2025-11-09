"""Memory-efficient tensor caching system."""

import numpy as np
import mmap
from pathlib import Path
import json
from typing import Dict, Optional, Union, Any
from collections import OrderedDict
import threading
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TensorCache:
    """Cache for efficient tensor storage and retrieval."""
    
    def __init__(self, cache_dir: Union[str, Path], max_size: int = 1024*1024*1024):
        """Initialize the tensor cache.
        
        Args:
            cache_dir: Directory for cache storage
            max_size: Maximum cache size in bytes (default 1GB)
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.current_size = 0
        self._cache: OrderedDict = OrderedDict()
        self._mmap_files: Dict[str, mmap.mmap] = {}
        self._lock = threading.Lock()
        self._load_metadata()
        
    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        meta_path = self.cache_dir / "meta" / "cache.json"
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "version": "1.0",
                "tensors": {},
                "cache_config": {
                    "max_size": self.max_size,
                    "eviction_policy": "lru",
                    "compression": "none"
                }
            }
            
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        meta_path = self.cache_dir / "meta" / "cache.json"
        with open(meta_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
            
    def get_tensor(self, tensor_name: str) -> Optional[np.ndarray]:
        """Retrieve a tensor from cache.
        
        Args:
            tensor_name: Name of the tensor to retrieve
            
        Returns:
            The tensor as a numpy array, or None if not found
        """
        with self._lock:
            # Check if tensor is already in memory cache
            if tensor_name in self._cache:
                # Update LRU order
                self._cache.move_to_end(tensor_name)
                return self._cache[tensor_name]
                
            # Check if tensor exists on disk
            if tensor_name not in self.metadata["tensors"]:
                return None
                
            # Load tensor from disk
            tensor_info = self.metadata["tensors"][tensor_name]
            tensor_path = Path(tensor_info["path"])
            
            if not tensor_path.exists():
                logger.warning(f"Tensor file missing: {tensor_path}")
                return None
                
            # Load tensor using memory mapping
            try:
                with open(tensor_path, "r+b") as f:
                    mm = mmap.mmap(f.fileno(), 0)
                    tensor = np.frombuffer(
                        mm,
                        dtype=np.dtype(tensor_info["dtype"])
                    ).reshape(tensor_info["shape"])
                    
                # Cache the tensor if there's room
                tensor_size = tensor.nbytes
                if self._ensure_cache_space(tensor_size):
                    self._cache[tensor_name] = tensor
                    self.current_size += tensor_size
                    self._mmap_files[tensor_name] = mm
                    
                return tensor
                
            except Exception as e:
                logger.error(f"Error loading tensor {tensor_name}: {e}")
                return None
                
    def put_tensor(self, tensor_name: str, tensor: np.ndarray) -> bool:
        """Store a tensor in the cache.
        
        Args:
            tensor_name: Name for the tensor
            tensor: The tensor to store
            
        Returns:
            True if storage was successful
        """
        with self._lock:
            tensor_size = tensor.nbytes
            
            # Ensure we have space
            if not self._ensure_cache_space(tensor_size):
                return False
                
            # Store tensor in memory cache
            self._cache[tensor_name] = tensor
            self.current_size += tensor_size
            
            # Save to disk
            tensor_path = self.cache_dir / "mapped" / f"{tensor_name}.bin"
            tensor.tofile(tensor_path)
            
            # Update metadata
            self.metadata["tensors"][tensor_name] = {
                "path": str(tensor_path),
                "shape": tensor.shape,
                "dtype": str(tensor.dtype),
                "size_bytes": tensor_size
            }
            self._save_metadata()
            
            return True
            
    def _ensure_cache_space(self, required_size: int) -> bool:
        """Ensure there's enough space in cache for new tensor.
        
        Args:
            required_size: Size in bytes needed
            
        Returns:
            True if space is available or was made available
        """
        while self.current_size + required_size > self.max_size and self._cache:
            # Evict oldest tensor (LRU policy)
            oldest_name, oldest_tensor = self._cache.popitem(last=False)
            self.current_size -= oldest_tensor.nbytes
            
            # Close memory map if it exists
            if oldest_name in self._mmap_files:
                self._mmap_files[oldest_name].close()
                del self._mmap_files[oldest_name]
                
        return self.current_size + required_size <= self.max_size
        
    def clear(self) -> None:
        """Clear all tensors from cache."""
        with self._lock:
            # Close all memory maps
            for mm in self._mmap_files.values():
                mm.close()
                
            self._cache.clear()
            self._mmap_files.clear()
            self.current_size = 0
            
    def __del__(self) -> None:
        """Cleanup when cache is destroyed."""
        try:
            self.clear()
        except:
            pass  # Ignore errors during cleanup