"""Streaming tensor operations for efficient model processing."""

import numpy as np
import mmap
from typing import Optional, Union, Tuple, Any
from pathlib import Path
import io
import threading
from concurrent.futures import ThreadPoolExecutor

class StreamingTensorOps:
    """Handles streaming tensor operations with memory efficiency."""
    
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self._lock = threading.Lock()
        
    def stream_quantize(self, 
                       tensor: Union[mmap.mmap, np.ndarray, Path, str],
                       dtype: np.dtype,
                       chunk_size: Optional[int] = None) -> np.ndarray:
        """Quantize a tensor using streaming to minimize memory usage.
        
        Args:
            tensor: Input tensor as memory map, numpy array, or path to tensor file
            dtype: Target dtype for quantization
            chunk_size: Optional custom chunk size for streaming
            
        Returns:
            Quantized tensor as numpy array
        """
        chunk_size = chunk_size or self.CHUNK_SIZE
        
        # Handle different input types
        if isinstance(tensor, (str, Path)):
            with open(tensor, 'rb') as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                return self._stream_quantize_mmap(mm, dtype, chunk_size)
        elif isinstance(tensor, mmap.mmap):
            return self._stream_quantize_mmap(tensor, dtype, chunk_size)
        elif isinstance(tensor, np.ndarray):
            return self._stream_quantize_array(tensor, dtype, chunk_size)
        else:
            raise TypeError(f"Unsupported tensor type: {type(tensor)}")
            
    def _stream_quantize_mmap(self,
                             mm: mmap.mmap,
                             dtype: np.dtype,
                             chunk_size: int) -> np.ndarray:
        """Stream quantize from a memory-mapped file."""
        # Get total size and shape
        mm.seek(0)
        header = np.frombuffer(mm.read(24), dtype=np.int64)  # Read shape information
        shape = tuple(header[:2])  # Assuming 2D tensor
        total_size = int(np.prod(shape))
        
        # Pre-allocate output array
        result = np.empty(shape, dtype=dtype)
        
        # Process in chunks
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk_data = np.frombuffer(
                    mm[start*8:(end*8)],  # Assuming float64 input
                    dtype=np.float64
                ).copy()  # Copy needed for threading safety
                
                futures.append(
                    executor.submit(
                        self._quantize_chunk,
                        chunk_data,
                        dtype,
                        start,
                        result
                    )
                )
                
            # Wait for all chunks to complete
            for future in futures:
                future.result()
                
        return result
        
    def _stream_quantize_array(self,
                              array: np.ndarray,
                              dtype: np.dtype,
                              chunk_size: int) -> np.ndarray:
        """Stream quantize from a numpy array."""
        shape = array.shape
        total_size = array.size
        result = np.empty(shape, dtype=dtype)
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk = array.ravel()[start:end].copy()
                
                futures.append(
                    executor.submit(
                        self._quantize_chunk,
                        chunk,
                        dtype,
                        start,
                        result
                    )
                )
                
            for future in futures:
                future.result()
                
        return result
        
    def _quantize_chunk(self,
                       chunk: np.ndarray,
                       dtype: np.dtype,
                       start_idx: int,
                       output: np.ndarray) -> None:
        """Quantize a single chunk and place in output array."""
        quantized = chunk.astype(dtype)
        
        with self._lock:
            output.ravel()[start_idx:start_idx + len(chunk)] = quantized
            
    def stream_compute(self,
                      tensor: Union[mmap.mmap, np.ndarray, Path, str],
                      operation: str,
                      chunk_size: Optional[int] = None,
                      **kwargs: Any) -> np.ndarray:
        """Perform streaming computation on a tensor.
        
        Args:
            tensor: Input tensor
            operation: Operation to perform ('mean', 'std', 'normalize', etc.)
            chunk_size: Optional custom chunk size
            **kwargs: Additional arguments for the operation
            
        Returns:
            Processed tensor
        """
        chunk_size = chunk_size or self.CHUNK_SIZE
        
        # Map operation names to functions
        op_map = {
            'mean': np.mean,
            'std': np.std,
            'normalize': self._normalize_chunk,
            'clip': np.clip
        }
        
        if operation not in op_map:
            raise ValueError(f"Unsupported operation: {operation}")
            
        op_func = op_map[operation]
        
        # Handle different input types similarly to stream_quantize
        if isinstance(tensor, (str, Path)):
            with open(tensor, 'rb') as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                return self._stream_compute_mmap(mm, op_func, chunk_size, **kwargs)
        elif isinstance(tensor, mmap.mmap):
            return self._stream_compute_mmap(tensor, op_func, chunk_size, **kwargs)
        elif isinstance(tensor, np.ndarray):
            return self._stream_compute_array(tensor, op_func, chunk_size, **kwargs)
        else:
            raise TypeError(f"Unsupported tensor type: {type(tensor)}")
            
    def _normalize_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """Normalize a chunk of data."""
        mean = np.mean(chunk)
        std = np.std(chunk)
        return (chunk - mean) / (std + 1e-8)
        
    def _stream_compute_mmap(self,
                           mm: mmap.mmap,
                           op_func: Any,
                           chunk_size: int,
                           **kwargs: Any) -> np.ndarray:
        """Stream compute from a memory-mapped file."""
        # Implementation similar to _stream_quantize_mmap but for general operations
        mm.seek(0)
        header = np.frombuffer(mm.read(24), dtype=np.int64)
        shape = tuple(header[:2])
        total_size = int(np.prod(shape))
        
        result = np.empty(shape, dtype=np.float32)
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk_data = np.frombuffer(
                    mm[start*8:end*8],
                    dtype=np.float64
                ).copy()
                
                futures.append(
                    executor.submit(
                        self._compute_chunk,
                        chunk_data,
                        op_func,
                        start,
                        result,
                        kwargs
                    )
                )
                
            for future in futures:
                future.result()
                
        return result
        
    def _compute_chunk(self,
                      chunk: np.ndarray,
                      op_func: Any,
                      start_idx: int,
                      output: np.ndarray,
                      kwargs: dict) -> None:
        """Apply computation to a single chunk."""
        processed = op_func(chunk, **kwargs) if kwargs else op_func(chunk)
        
        with self._lock:
            output.ravel()[start_idx:start_idx + len(chunk)] = processed
            
    def _stream_compute_array(self,
                            array: np.ndarray,
                            op_func: Any,
                            chunk_size: int,
                            **kwargs: Any) -> np.ndarray:
        """Stream compute from a numpy array."""
        shape = array.shape
        total_size = array.size
        result = np.empty(shape, dtype=np.float32)
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            
            for start in range(0, total_size, chunk_size):
                end = min(start + chunk_size, total_size)
                chunk = array.ravel()[start:end].copy()
                
                futures.append(
                    executor.submit(
                        self._compute_chunk,
                        chunk,
                        op_func,
                        start,
                        result,
                        kwargs
                    )
                )
                
            for future in futures:
                future.result()
                
        return result