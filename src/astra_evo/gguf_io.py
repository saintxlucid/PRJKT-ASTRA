"""GGUF file I/O operations for model evolution."""
from __future__ import annotations
from pathlib import Path
import json
import struct
import mmap
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, BinaryIO, Any, TypeVar
import logging

T = TypeVar('T', str, int, float, bytes)  # Type variable for KV store values

logger = logging.getLogger(__name__)

class GGUFError(Exception):
    """Base exception for GGUF operations."""
    pass

class GGUFIO:
    """Handles reading and writing of GGUF model files."""
    
    MAGIC = 0x46554747  # 'GGUF' in little endian
    TENSOR_TYPES = {
        0: np.float32,
        1: np.float16,
        2: np.int8,
        3: np.int16,
        4: np.int32
    }
    
    def __init__(self, path: str):
        """Initialize GGUF file handler.
        
        Args:
            path: Path to GGUF file
        """
        self.path = Path(path)
        self._file: Optional[BinaryIO] = None
        self._mmap: Optional[mmap.mmap] = None
        self._tensor_offsets: Dict[str, int] = {}
        self.kv: Dict[str, Union[str, int, float, bytes]] = {}
        self.header: Dict[str, int] = {}
        
        # For development/testing without real GGUF files
        self._dev_mode = not path.endswith('.gguf')
        self._kv_path = self.path.with_suffix('.kv.json') if self._dev_mode else None
        
        if self._dev_mode and self._kv_path and self._kv_path.exists():
            self.kv = json.loads(self._kv_path.read_text(encoding='utf-8'))
            logger.debug(f"Loaded dev mode KV from {self._kv_path}")
            return
            
        if not self.path.exists():
            logger.warning(f"GGUF file not found: {self.path}")
            return
            
        try:
            self._file = open(self.path, 'rb')
            self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            self._read_header()
            self._read_metadata()
            logger.debug(f"Initialized GGUF file: {self.path}")
        except Exception as e:
            logger.error(f"Failed to initialize GGUF file {self.path}: {e}")
            if self._mmap:
                self._mmap.close()
            if self._file:
                self._file.close()
            raise GGUFError(f"GGUF initialization failed: {e}")
            
    def __del__(self):
        """Clean up file handles."""
        if self._mmap:
            self._mmap.close()
        if self._file:
            self._file.close()
            
    def _read_header(self) -> None:
        """Read GGUF header section."""
        if not self._mmap:
            raise GGUFError("No file mapped")
            
        try:
            magic = struct.unpack('<I', self._mmap[0:4])[0]
            if magic != self.MAGIC:
                raise GGUFError(f"Invalid GGUF magic: {hex(magic)}")
                
            version = struct.unpack('<I', self._mmap[4:8])[0]
            tensor_count = struct.unpack('<Q', self._mmap[8:16])[0]
            kv_count = struct.unpack('<Q', self._mmap[16:24])[0]
            
            self.header = {
                'version': version,
                'tensor_count': tensor_count,
                'kv_count': kv_count
            }
            logger.debug(f"Read GGUF header: v{version}, {tensor_count} tensors, {kv_count} KV pairs")
            
        except struct.error as e:
            raise GGUFError(f"Failed to parse GGUF header: {e}")
            
    def get_value(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get typed value from KV store.
        
        Args:
            key: Key to lookup
            default: Default value if key not found
            
        Returns:
            Value of type T or None if not found
        """
        val = self.kv.get(key, default)
        if isinstance(val, (bytes, str)):
            return str(val)  # type: ignore
        if isinstance(val, (int, float)):
            return val  # type: ignore
        return default

    def set_value(self, key: str, value: Union[str, int, float, bytes]) -> None:
        """Set value in KV store with dev mode file saving.
        
        Args:
            key: Key to set
            value: Value to store
        """
        self.kv[key] = value
        if self._dev_mode and self._kv_path:
            with open(self._kv_path, 'w', encoding='utf-8') as f:
                json.dump(self.kv, f, indent=2)
        
    def _read_metadata(self) -> None:
        """Read key-value metadata section."""
        offset = 24  # After header
        
        # Read KV pairs
        for _ in range(self.header['kv_count']):
            # Read key length and key
            key_len = struct.unpack('<Q', self._mmap[offset:offset+8])[0]
            offset += 8
            key = self._mmap[offset:offset+key_len].decode('utf-8')
            offset += key_len
            
            # Read value type and value
            val_type = struct.unpack('<I', self._mmap[offset:offset+4])[0]
            offset += 4
            
            if val_type == 0:  # uint8
                val = struct.unpack('<B', self._mmap[offset:offset+1])[0]
                offset += 1
            elif val_type == 1:  # int8  
                val = struct.unpack('<b', self._mmap[offset:offset+1])[0]
                offset += 1
            elif val_type == 2:  # uint16
                val = struct.unpack('<H', self._mmap[offset:offset+2])[0] 
                offset += 2
            elif val_type == 3:  # int16
                val = struct.unpack('<h', self._mmap[offset:offset+2])[0]
                offset += 2
            elif val_type == 4:  # uint32
                val = struct.unpack('<I', self._mmap[offset:offset+4])[0]
                offset += 4
            elif val_type == 5:  # int32
                val = struct.unpack('<i', self._mmap[offset:offset+4])[0]
                offset += 4
            elif val_type == 6:  # float32
                val = struct.unpack('<f', self._mmap[offset:offset+4])[0]
                offset += 4
            elif val_type == 7:  # string
                str_len = struct.unpack('<Q', self._mmap[offset:offset+8])[0]
                offset += 8
                val = self._mmap[offset:offset+str_len].decode('utf-8')
                offset += str_len
            else:
                raise ValueError(f"Unknown value type: {val_type}")
                
            self.kv[key] = val

    def kv_get(self, key: str, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key: str, value):
        self.kv[key] = value

    def save_kv(self):
        self.kv_path.write_text(json.dumps(self.kv, indent=2), encoding="utf-8")

def supports_rope(io: GGUFIO) -> bool:
    """Check if model architecture supports RoPE tuning."""
    arch = str(io.get_value("general.arch") or io.get_value("arch") or "").lower()
    return any(x in arch for x in ["gpt", "llama"])

def apply_rope_tuning(path: str, rope_base: float, rope_scale: float) -> None:
    """Apply RoPE tuning parameters to model.
    
    Args:
        path: Path to GGUF file
        rope_base: RoPE base value
        rope_scale: RoPE scaling factor (0.8-1.6)
    
    Raises:
        GGUFError: If model doesn't support RoPE or invalid parameters
    """
    io = GGUFIO(path)
    if not supports_rope(io):
        raise GGUFError("RoPE not supported by model architecture")
    if not (0.8 <= rope_scale <= 1.6):
        raise GGUFError("rope_scale must be between 0.8 and 1.6")
    io.set_value("rope.base", rope_base)
    io.set_value("rope.scale", rope_scale)
    if io._dev_mode and io._kv_path:
        with open(io._kv_path, 'w', encoding='utf-8') as f:
            json.dump(io.kv, f, indent=2)
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self.header = {}
        self.kv_dict = {}
        self.tensors = {}
        
    def read_header(self) -> Dict:
        """Read GGUF header and return metadata."""
        with open(self.path, 'rb') as f:
            magic = struct.unpack('I', f.read(4))[0]
            if magic != self.MAGIC:
                raise ValueError(f"Invalid GGUF file: {self.path}")
                
            version = struct.unpack('I', f.read(4))[0]
            tensor_count = struct.unpack('Q', f.read(8))[0]
            kv_count = struct.unpack('Q', f.read(8))[0]
            
            self.header = {
                'version': version,
                'tensor_count': tensor_count,
                'kv_count': kv_count
            }
            return self.header
            
    def read_kv(self) -> Dict[str, Union[str, int, float, bytes]]:
        """Read key-value metadata section.
        
        Returns:
            Dictionary of metadata key-value pairs
            
        Raises:
            GGUFError: If file not mapped
        """
        if not self._mmap:
            raise GGUFError("No file mapped")
            
        offset = 24  # After header
        result = {}
        
        try:
            for _ in range(self.header.get('kv_count', 0)):
                key_len = struct.unpack('<Q', self._mmap[offset:offset+8])[0]
                offset += 8
                key = self._mmap[offset:offset+key_len].decode('utf-8')
                offset += key_len
                
                # Read value type
                val_type = struct.unpack('<I', self._mmap[offset:offset+4])[0]
                offset += 4
                
                # Read value based on type
                if val_type in [0, 1]:  # uint8/int8
                    val = struct.unpack('<B' if val_type == 0 else '<b', 
                                      self._mmap[offset:offset+1])[0]
                    offset += 1
                elif val_type in [2, 3]:  # uint16/int16
                    val = struct.unpack('<H' if val_type == 2 else '<h',
                                      self._mmap[offset:offset+2])[0]
                    offset += 2
                elif val_type in [4, 5]:  # uint32/int32
                    val = struct.unpack('<I' if val_type == 4 else '<i',
                                      self._mmap[offset:offset+4])[0]
                    offset += 4
                elif val_type == 6:  # float32
                    val = struct.unpack('<f', self._mmap[offset:offset+4])[0]
                    offset += 4
                elif val_type == 7:  # string
                    str_len = struct.unpack('<Q', self._mmap[offset:offset+8])[0]
                    offset += 8
                    val = self._mmap[offset:offset+str_len].decode('utf-8')
                    offset += str_len
                else:
                    raise GGUFError(f"Unknown value type: {val_type}")
                    
                result[key] = val
            
            return result
            
        except struct.error as e:
            raise GGUFError(f"Failed to parse KV data: {e}")
        
    def read_tensor(self, name: str) -> np.ndarray:
        """Read specific tensor by name.
        
        Args:
            name: Name of tensor to read
            
        Returns:
            Numpy array containing tensor data
            
        Raises:
            GGUFError: If tensor not found
        """
        if name not in self.tensors:
            raise GGUFError(f"Tensor not found: {name}")
            
        info = self.tensors[name]
        with open(self.path, 'rb') as f:
            f.seek(info['offset'])
            raw = f.read(info['size'])
            data = np.frombuffer(raw, dtype=info['dtype'])
            return data.reshape(info['shape'])
        
    def write_header(self, tensor_count: int, kv_count: int) -> None:
        """Write GGUF header.
        
        Args:
            tensor_count: Number of tensors
            kv_count: Number of KV pairs
        """
        with open(self.path, 'wb') as f:
            f.write(struct.pack('I', self.MAGIC))
            f.write(struct.pack('I', 1))  # version
            f.write(struct.pack('Q', tensor_count))
            f.write(struct.pack('Q', kv_count))
            
    def write_kv(self, key: str, value: Union[str, int, float, bytes]) -> None:
        """Write key-value metadata pair.
        
        Args:
            key: Key name
            value: Value to write
        """
        with open(self.path, 'ab') as f:
            # Write key
            key_bytes = key.encode('utf-8')
            f.write(struct.pack('Q', len(key_bytes)))
            f.write(key_bytes)
            
            # Write value based on type
            if isinstance(value, str):
                f.write(struct.pack('I', 7))  # string type
                val_bytes = value.encode('utf-8')
                f.write(struct.pack('Q', len(val_bytes)))
                f.write(val_bytes)
            elif isinstance(value, int):
                f.write(struct.pack('I', 4))  # int32 type
                f.write(struct.pack('i', value))
            elif isinstance(value, float):
                f.write(struct.pack('I', 6))  # float32 type
                f.write(struct.pack('f', value))
            elif isinstance(value, bytes):
                f.write(struct.pack('I', 0))  # uint8 type
                f.write(value)
        
    def write_tensor(self, name: str, data: np.ndarray) -> None:
        """Write tensor data.
        
        Args:
            name: Tensor name
            data: Numpy array to write
        """
        with open(self.path, 'ab') as f:
            # Record tensor info
            offset = f.tell()
            self.tensors[name] = {
                'offset': offset,
                'size': data.nbytes,
                'dtype': data.dtype,
                'shape': data.shape
            }
            
            # Write tensor data
            f.write(data.tobytes())
        
    def quantize_tensor(self, data: np.ndarray, qtype: str) -> np.ndarray:
        """Quantize tensor to specified format.
        
        Args:
            data: Input tensor data
            qtype: Quantization type ('Q4_K_M' or 'Q5_K_M')
            
        Returns:
            Quantized tensor data
            
        Raises:
            ValueError: If qtype not supported
        """
        if qtype not in ['Q4_K_M', 'Q5_K_M']:
            raise ValueError(f"Unsupported quantization type: {qtype}")
            
        quantizer = QuantizedTensor(qtype)
        quantized, _ = quantizer.quantize(data)
        return quantized
        
    def repack_tensors(self, names: List[str]) -> None:
        """Repack tensors for optimal layout."""
        # Implementation for tensor repacking
        pass

class QuantizedTensor:
    """Handles tensor quantization operations."""
    
    def __init__(self, dtype: str):
        self.dtype = dtype
        
    def quantize(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Quantize FP16 tensor to target type."""
        if self.dtype == 'Q5_K_M':
            return self._q5_k_m_quantize(data)
        elif self.dtype == 'Q4_K_M':
            return self._q4_k_m_quantize(data)
        else:
            raise ValueError(f"Unsupported quantization type: {self.dtype}")
            
    def _q5_k_m_quantize(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Q5_K_M quantization.
        
        Args:
            data: Input FP16 tensor
            
        Returns:
            Tuple of (quantized tensor, metadata)
        """
        # Ensure input is float16
        if data.dtype != np.float16:
            data = data.astype(np.float16)
            
        # Calculate scaling factors per block
        block_size = 32
        n_blocks = data.size // block_size
        scales = np.zeros(n_blocks, dtype=np.float16)
        
        for i in range(n_blocks):
            block = data[i*block_size:(i+1)*block_size]
            amax = np.max(np.abs(block))
            scale = amax / 16 if amax != 0 else 1
            scales[i] = scale
            
        # Quantize blocks
        quantized = np.zeros(data.size, dtype=np.int8)
        for i in range(n_blocks):
            block = data[i*block_size:(i+1)*block_size]
            scale = scales[i]
            qblock = np.round(block / scale).clip(-16, 15)
            quantized[i*block_size:(i+1)*block_size] = qblock.astype(np.int8)
            
        metadata = {
            'scales': scales,
            'block_size': block_size,
            'original_dtype': str(data.dtype),
            'original_shape': data.shape
        }
        
        return quantized, metadata
        
    def _q4_k_m_quantize(self, data: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Q4_K_M quantization.
        
        Args:
            data: Input FP16 tensor
            
        Returns:
            Tuple of (quantized tensor, metadata)
        """
        # Ensure input is float16
        if data.dtype != np.float16:
            data = data.astype(np.float16)
            
        # Calculate scaling factors per block
        block_size = 32
        n_blocks = data.size // block_size
        scales = np.zeros(n_blocks, dtype=np.float16)
        zeros = np.zeros(n_blocks, dtype=np.float16)
        
        for i in range(n_blocks):
            block = data[i*block_size:(i+1)*block_size]
            amax = np.max(np.abs(block))
            amin = np.min(block)
            scale = (amax - amin) / 15 if amax != amin else 1
            zeros[i] = amin
            scales[i] = scale
            
        # Quantize blocks
        quantized = np.zeros(data.size, dtype=np.int8)
        for i in range(n_blocks):
            block = data[i*block_size:(i+1)*block_size]
            scale = scales[i]
            zero = zeros[i]
            qblock = np.round((block - zero) / scale).clip(0, 15)
            quantized[i*block_size:(i+1)*block_size] = qblock.astype(np.int8)
            
        metadata = {
            'scales': scales,
            'zeros': zeros,
            'block_size': block_size,
            'original_dtype': str(data.dtype),
            'original_shape': data.shape
        }
        
        return quantized, metadata