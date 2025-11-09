import base64
import json
from typing import Dict, Any

try:
    import zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    print("Warning: zstd not available. Compression will be disabled.")

def compress_payload(payload: Dict, level: int = 3) -> Dict:
    """Compress a payload using zstd"""
    if not ZSTD_AVAILABLE:
        return payload
    
    try:
        # Convert payload to JSON string
        payload_str = json.dumps(payload, separators=(",", ":"))
        
        # Compress using zstd
        compressed = zstd.compress(payload_str.encode(), level)
        
        # Return compressed payload with metadata
        return {
            "compressed": True,
            "algorithm": "zstd",
            "level": level,
            "data": base64.b64encode(compressed).decode(),
            "original_size": len(payload_str)
        }
    except Exception as e:
        print(f"Compression failed: {e}")
        return payload

def decompress_payload(payload: Dict) -> Dict:
    """Decompress a payload using zstd"""
    if not ZSTD_AVAILABLE:
        return payload
    
    # Check if payload is compressed
    if not isinstance(payload, dict) or not payload.get("compressed"):
        return payload
    
    try:
        # Decode base64 data
        compressed_data = base64.b64decode(payload["data"])
        
        # Decompress using zstd
        decompressed = zstd.decompress(compressed_data)
        
        # Parse JSON
        return json.loads(decompressed.decode())
    except Exception as e:
        print(f"Decompression failed: {e}")
        return payload

def is_compressed(payload: Dict) -> bool:
    """Check if a payload is compressed"""
    return isinstance(payload, dict) and payload.get("compressed", False)