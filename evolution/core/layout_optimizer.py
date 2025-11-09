"""Optimized on-disk layout management for model files."""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path
import mmap
import os
import logging
import struct
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import shutil

logger = logging.getLogger(__name__)

@dataclass
class TensorLocation:
    """Physical location of a tensor on disk."""
    offset: int
    size: int
    alignment: int
    is_contiguous: bool
    access_pattern: str  # 'sequential', 'random', or 'rare'

@dataclass
class LayoutBlock:
    """A block of the file layout."""
    start: int
    size: int
    tensor_name: Optional[str]
    is_free: bool
    alignment: int

class DiskLayoutOptimizer:
    """Optimizes model file layout for efficient access patterns."""
    
    ALIGNMENT_SIZES = {
        'default': 64,      # Default alignment
        'critical': 4096,   # Page alignment for critical tensors
        'standard': 256,    # Standard tensor alignment
        'compact': 8        # Minimal alignment for small tensors
    }
    
    def __init__(self, 
                 max_workers: int = 4,
                 page_size: int = 4096):
        """Initialize the layout optimizer.
        
        Args:
            max_workers: Maximum number of parallel workers
            page_size: System page size (usually 4KB)
        """
        self.max_workers = max_workers
        self.page_size = page_size
        self._access_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'sequential_reads': 0,
            'random_reads': 0,
            'total_bytes_read': 0
        })
        
    def analyze_access_patterns(self,
                              model_path: Path,
                              access_logs: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze tensor access patterns from logs.
        
        Args:
            model_path: Path to model file
            access_logs: List of access records
            
        Returns:
            Dictionary mapping tensor names to access patterns
        """
        # Process access logs
        for log in access_logs:
            tensor_name = log['tensor']
            access_type = log['type']
            bytes_read = log['bytes']
            
            stats = self._access_stats[tensor_name]
            stats['total_bytes_read'] += bytes_read
            
            if access_type == 'sequential':
                stats['sequential_reads'] += 1
            else:
                stats['random_reads'] += 1
                
        # Classify access patterns
        patterns = {}
        for tensor_name, stats in self._access_stats.items():
            total_reads = stats['sequential_reads'] + stats['random_reads']
            if total_reads == 0:
                patterns[tensor_name] = 'rare'
            elif stats['sequential_reads'] / total_reads > 0.8:
                patterns[tensor_name] = 'sequential'
            else:
                patterns[tensor_name] = 'random'
                
        return patterns
        
    def optimize_layout(self,
                       model_path: Path,
                       tensors: Dict[str, np.ndarray],
                       access_patterns: Optional[Dict[str, str]] = None) -> Path:
        """Optimize model file layout.
        
        Args:
            model_path: Path to model file
            tensors: Dictionary of tensors
            access_patterns: Optional pre-analyzed access patterns
            
        Returns:
            Path to optimized model file
        """
        if access_patterns is None:
            access_patterns = {name: 'sequential' for name in tensors}
            
        # Calculate optimal locations
        locations = self._calculate_optimal_locations(tensors, access_patterns)
        
        # Create optimized file
        optimized_path = model_path.with_suffix('.optimized.bin')
        self._write_optimized_file(optimized_path, tensors, locations)
        
        return optimized_path
        
    def _calculate_optimal_locations(self,
                                   tensors: Dict[str, np.ndarray],
                                   access_patterns: Dict[str, str]) -> Dict[str, TensorLocation]:
        """Calculate optimal tensor locations."""
        locations: Dict[str, TensorLocation] = {}
        current_offset = 0
        
        # Sort tensors by access pattern and size
        sorted_tensors = sorted(
            tensors.items(),
            key=lambda x: (
                self._get_pattern_priority(access_patterns[x[0]]),
                -x[1].nbytes
            )
        )
        
        # Assign locations
        for name, tensor in sorted_tensors:
            alignment = self._get_alignment(
                tensor.nbytes,
                access_patterns[name]
            )
            
            # Align offset
            current_offset = self._align_offset(current_offset, alignment)
            
            locations[name] = TensorLocation(
                offset=current_offset,
                size=tensor.nbytes,
                alignment=alignment,
                is_contiguous=True,
                access_pattern=access_patterns[name]
            )
            
            current_offset += tensor.nbytes
            
        return locations
        
    def _get_pattern_priority(self, pattern: str) -> int:
        """Get priority for access pattern."""
        return {
            'sequential': 0,  # Place sequential access tensors first
            'random': 1,     # Then random access tensors
            'rare': 2       # Rarely accessed tensors last
        }[pattern]
        
    def _get_alignment(self, size: int, pattern: str) -> int:
        """Get alignment requirement for tensor."""
        if pattern == 'random' and size > 1024*1024:
            return self.ALIGNMENT_SIZES['critical']  # Page align large random access tensors
        elif pattern == 'sequential' and size > 1024*1024:
            return self.ALIGNMENT_SIZES['standard']  # Standard align large sequential tensors
        elif size < 1024:
            return self.ALIGNMENT_SIZES['compact']   # Minimal align small tensors
        else:
            return self.ALIGNMENT_SIZES['default']   # Default alignment
            
    def _align_offset(self, offset: int, alignment: int) -> int:
        """Align an offset to specified boundary."""
        return ((offset + alignment - 1) // alignment) * alignment
        
    def _write_optimized_file(self,
                             output_path: Path,
                             tensors: Dict[str, np.ndarray],
                             locations: Dict[str, TensorLocation]) -> None:
        """Write tensors to optimized file layout."""
        # Calculate total size
        total_size = max(
            loc.offset + loc.size
            for loc in locations.values()
        )
        
        # Create file with total size
        with open(output_path, 'wb') as f:
            f.truncate(total_size)
            
        # Write tensors in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for name, tensor in tensors.items():
                location = locations[name]
                futures.append(
                    executor.submit(
                        self._write_tensor,
                        output_path,
                        tensor,
                        location
                    )
                )
                
            # Wait for all writes to complete
            for future in futures:
                future.result()
                
        # Write layout metadata
        meta_path = output_path.with_suffix('.layout.json')
        layout_meta = {
            'version': '1.0',
            'page_size': self.page_size,
            'total_size': total_size,
            'tensors': {
                name: {
                    'offset': loc.offset,
                    'size': loc.size,
                    'alignment': loc.alignment,
                    'access_pattern': loc.access_pattern
                }
                for name, loc in locations.items()
            }
        }
        
        with open(meta_path, 'w') as f:
            json.dump(layout_meta, f, indent=2)
            
    def _write_tensor(self,
                     file_path: Path,
                     tensor: np.ndarray,
                     location: TensorLocation) -> None:
        """Write a tensor to its optimized location."""
        with open(file_path, 'r+b') as f:
            f.seek(location.offset)
            tensor.tofile(f)
            
    def verify_layout(self, file_path: Path) -> Dict[str, Any]:
        """Verify optimized file layout.
        
        Args:
            file_path: Path to optimized model file
            
        Returns:
            Verification results
        """
        meta_path = file_path.with_suffix('.layout.json')
        with open(meta_path, 'r') as f:
            layout_meta = json.load(f)
            
        results = {
            'verified': True,
            'errors': [],
            'stats': {
                'total_size': layout_meta['total_size'],
                'tensor_count': len(layout_meta['tensors']),
                'alignment_stats': defaultdict(int)
            }
        }
        
        # Verify each tensor
        with open(file_path, 'rb') as f:
            for name, info in layout_meta['tensors'].items():
                # Check alignment
                if info['offset'] % info['alignment'] != 0:
                    results['errors'].append(
                        f"Tensor {name} misaligned: "
                        f"offset {info['offset']} not aligned to {info['alignment']}"
                    )
                    results['verified'] = False
                    
                # Track alignment stats
                results['stats']['alignment_stats'][info['alignment']] += 1
                
                # Verify data presence
                f.seek(info['offset'])
                data = f.read(info['size'])
                if len(data) != info['size']:
                    results['errors'].append(
                        f"Tensor {name} data incomplete: "
                        f"expected {info['size']} bytes, got {len(data)}"
                    )
                    results['verified'] = False
                    
        return results
        
    def defragment(self, file_path: Path) -> Dict[str, Any]:
        """Defragment model file layout.
        
        Args:
            file_path: Path to model file
            
        Returns:
            Defragmentation results
        """
        meta_path = file_path.with_suffix('.layout.json')
        with open(meta_path, 'r') as f:
            layout_meta = json.load(f)
            
        # Create list of blocks
        blocks: List[LayoutBlock] = []
        for name, info in layout_meta['tensors'].items():
            blocks.append(LayoutBlock(
                start=info['offset'],
                size=info['size'],
                tensor_name=name,
                is_free=False,
                alignment=info['alignment']
            ))
            
        # Sort blocks by start offset
        blocks.sort(key=lambda b: b.start)
        
        # Find and merge free spaces
        optimized_blocks = self._merge_free_blocks(blocks)
        
        # Calculate fragmentation metrics
        metrics = self._calculate_fragmentation_metrics(optimized_blocks)
        
        if metrics['fragmentation_ratio'] > 0.1:  # More than 10% fragmentation
            # Create defragmented file
            defrag_path = file_path.with_suffix('.defrag.bin')
            self._create_defragmented_file(
                file_path,
                defrag_path,
                layout_meta,
                optimized_blocks
            )
            
            # Update layout metadata
            layout_meta['tensors'] = self._update_layout_metadata(optimized_blocks)
            with open(meta_path, 'w') as f:
                json.dump(layout_meta, f, indent=2)
                
            # Replace original with defragmented file
            shutil.move(defrag_path, file_path)
            
        return metrics
        
    def _merge_free_blocks(self, blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """Merge adjacent free blocks."""
        if not blocks:
            return []
            
        result = [blocks[0]]
        for block in blocks[1:]:
            prev = result[-1]
            if prev.is_free and block.is_free:
                # Merge adjacent free blocks
                prev.size += block.size
            else:
                result.append(block)
                
        return result
        
    def _calculate_fragmentation_metrics(self, blocks: List[LayoutBlock]) -> Dict[str, float]:
        """Calculate fragmentation metrics."""
        total_size = sum(block.size for block in blocks)
        free_space = sum(block.size for block in blocks if block.is_free)
        free_blocks = sum(1 for block in blocks if block.is_free)
        
        return {
            'total_size': total_size,
            'free_space': free_space,
            'free_blocks': free_blocks,
            'fragmentation_ratio': free_space / total_size if total_size > 0 else 0.0
        }
        
    def _create_defragmented_file(self,
                                 source_path: Path,
                                 target_path: Path,
                                 layout_meta: Dict[str, Any],
                                 blocks: List[LayoutBlock]) -> None:
        """Create defragmented file."""
        with open(source_path, 'rb') as src, open(target_path, 'wb') as dst:
            for block in blocks:
                if not block.is_free:
                    # Copy tensor data
                    src.seek(layout_meta['tensors'][block.tensor_name]['offset'])
                    data = src.read(block.size)
                    dst.write(data)
                else:
                    # Write zeros for free space
                    dst.write(b'\0' * block.size)