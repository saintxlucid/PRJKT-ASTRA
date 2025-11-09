import json
import base64
from typing import Dict, List, Iterator, Optional
from core import aicl_core

class StreamChunk:
    """Represents a chunk in a streaming message"""
    
    def __init__(self, sequence: int, data: str, final: bool = False):
        self.sequence = sequence
        self.data = data
        self.final = final
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "sequence": self.sequence,
            "data": self.data,
            "final": self.final
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StreamChunk':
        """Create from dictionary representation"""
        return cls(
            sequence=data["sequence"],
            data=data["data"],
            final=data.get("final", False)
        )

def create_stream_message(
    frm: str, 
    to: str, 
    topic: str, 
    chunks: List[StreamChunk],
    ctx: Optional[Dict] = None
) -> Dict:
    """Create a streaming message with multiple chunks"""
    return {
        "v": "aicl/1.0",
        "id": f"stream_{frm}_{to}_{topic}",
        "ts": __import__('time').strftime("%Y-%m-%dT%H:%M:%SZ", __import__('time').gmtime()),
        "from": frm,
        "to": to,
        "act": "stream",
        "topic": topic,
        "ctx": ctx or {},
        "payload": {
            "chunks": [chunk.to_dict() for chunk in chunks]
        },
        "sig": None
    }

def split_large_content(
    content: str, 
    chunk_size: int = 1024
) -> List[StreamChunk]:
    """Split large content into chunks for streaming"""
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunk_data = content[i:i + chunk_size]
        final = (i + chunk_size) >= len(content)
        chunks.append(StreamChunk(i // chunk_size, chunk_data, final))
    return chunks

def reconstruct_stream_content(chunks: List[Dict]) -> str:
    """Reconstruct content from stream chunks"""
    # Sort chunks by sequence number
    sorted_chunks = sorted(chunks, key=lambda x: x["sequence"])
    return "".join(chunk["data"] for chunk in sorted_chunks)

def stream_large_payload(
    payload: Dict, 
    max_chunk_size: int = 1024
) -> Iterator[Dict]:
    """Stream a large payload as multiple messages"""
    # Convert payload to JSON string
    payload_str = json.dumps(payload, separators=(",", ":"))
    
    # Split into chunks
    for i in range(0, len(payload_str), max_chunk_size):
        chunk_data = payload_str[i:i + max_chunk_size]
        final = (i + max_chunk_size) >= len(payload_str)
        
        yield {
            "sequence": i // max_chunk_size,
            "data": base64.b64encode(chunk_data.encode()).decode(),
            "final": final
        }

def reconstruct_payload_from_stream(chunks: List[Dict]) -> Dict:
    """Reconstruct payload from stream chunks"""
    # Sort chunks by sequence number
    sorted_chunks = sorted(chunks, key=lambda x: x["sequence"])
    
    # Decode and concatenate
    payload_data = ""
    for chunk in sorted_chunks:
        payload_data += base64.b64decode(chunk["data"]).decode()
    
    # Parse JSON
    return json.loads(payload_data)