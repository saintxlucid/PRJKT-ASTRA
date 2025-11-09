"""
ASTRA LLM Server Configuration
Manages llama.cpp server startup and configuration.
Created: October 16, 2025
"""
from typing import Dict, List, Optional
from pathlib import Path
import subprocess
import json
import structlog
from .metadata import MetadataHandler, AstraMetadata

logger = structlog.get_logger()

class LLMServerConfig:
    """LLM server configuration and startup"""
    
    # GGUF magic bytes and version info
    GGUF_MAGIC = b'GGUF'
    GGUF_VERSION = 2  # Current version as of Oct 2025
    GGUF_HEADER_SIZE = 16  # Basic header size: magic(4) + version(4) + tensor_count(8)
    
    def __init__(
        self,
        model_path: Path,
        grammar_path: Optional[Path] = None,
        lora_paths: Optional[List[tuple[Path, float]]] = None,
        host: str = "127.0.0.1",
        port: int = 8001
    ):
        """
        Initialize server configuration
        Args:
            model_path: Path to GGUF model
            grammar_path: Optional path to GBNF grammar file
            lora_paths: Optional list of (path, scale) tuples for LoRA adapters
            host: Server host
            port: Server port
            
        Raises:
            ValueError: If model file is invalid or corrupted
        """
        self.model_path = model_path
        self.grammar_path = grammar_path
        self.lora_paths = lora_paths or []
        self.host = host
        self.port = port
        
        # Validate GGUF header before proceeding
        self._validate_gguf_header(model_path)
        
        # Load metadata from model
        self.metadata = MetadataHandler(model_path)
        
        # Paths to llama.cpp binaries
        self.server_binary = Path("llama.cpp/llama-server")
        self.quantize_binary = Path("llama.cpp/quantize")
        
        logger.info(
            "Initialized LLM server config",
            model=str(model_path),
            metadata_version=self.metadata.metadata.identity_version
        )
        
    def _validate_gguf_header(self, model_path: Path) -> None:
        """
        Validate GGUF model file header.
        
        Args:
            model_path: Path to GGUF model file
            
        Raises:
            ValueError: If header is invalid or file is corrupted
            FileNotFoundError: If model file doesn't exist
            IOError: If file read fails
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        file_size = model_path.stat().st_size
        if file_size < self.GGUF_HEADER_SIZE:
            raise ValueError(
                f"Model file too small ({file_size} bytes) to be valid GGUF. "
                f"Minimum size is {self.GGUF_HEADER_SIZE} bytes."
            )
        
        try:
            with open(model_path, 'rb') as f:
                # Read and validate magic bytes
                magic = f.read(4)
                if magic != self.GGUF_MAGIC:
                    raise ValueError(
                        f"Invalid GGUF magic bytes: {magic!r}, "
                        f"expected {self.GGUF_MAGIC!r}"
                    )
                
                # Read and validate version
                version = int.from_bytes(f.read(4), 'little')
                if version != self.GGUF_VERSION:
                    logger.warning(
                        f"Unexpected GGUF version: {version}, "
                        f"expected {self.GGUF_VERSION}. Model may be incompatible."
                    )
                
                # Read tensor count (sanity check for corruption)
                tensor_count = int.from_bytes(f.read(8), 'little')
                if tensor_count <= 0 or tensor_count > 10000:  # Reasonable limits
                    raise ValueError(
                        f"Invalid tensor count in GGUF header: {tensor_count}. "
                        "Model file may be corrupted."
                    )
                
                # Try reading a bit more to check for truncation
                try:
                    f.seek(-16, 2)  # Try reading last 16 bytes
                    f.read(16)
                except (IOError, OSError):
                    raise ValueError(
                        "Model file appears to be truncated. "
                        "Please re-download or repair the file."
                    )
                
        except (IOError, OSError) as e:
            raise IOError(f"Failed to read model file: {e}")
            
        logger.info(
            "GGUF header validation passed",
            path=str(model_path),
            version=version,
            tensor_count=tensor_count
        )
    
    def get_server_args(self) -> List[str]:
        """Build llama-server command arguments"""
        args = [
            str(self.server_binary),
            "--model", str(self.model_path),
            "--host", self.host,
            "--port", str(self.port)
        ]
        
        # Add grammar if specified
        if self.grammar_path:
            args.extend(["--grammar-file", str(self.grammar_path)])
        
        # Add LoRA adapters
        for path, scale in self.lora_paths:
            args.extend(["--lora", f"{path}:{scale}"])
        
        # Add sampling params
        sampling = self.metadata.get_sampling_args()
        args.extend([
            "--temp", str(sampling["temperature"]),
            "--top-p", str(sampling["top_p"]),
            "--repeat-penalty", str(sampling["repeat_penalty"])
        ])
        
        if "top_k" in sampling:
            args.extend(["--top-k", str(sampling["top_k"])])
        
        # Add RoPE params if present
        rope = self.metadata.get_rope_args()
        if rope.get("scaling"):
            args.extend(["--rope-scaling", rope["scaling"]])
        if rope.get("freq_base"):
            args.extend(["--rope-freq-base", str(rope["freq_base"])])
        if rope.get("freq_scale"):
            args.extend(["--rope-freq-scale", str(rope["freq_scale"])])
        
        return args
    
    def start_server(self) -> subprocess.Popen:
        """Start the llama.cpp server process"""
        args = self.get_server_args()
        
        logger.info(
            "Starting LLM server",
            command=" ".join(args)
        )
        
        return subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    def quantize_model(
        self,
        input_path: Path,
        output_path: Path,
        quant_type: str = "q4_k_m"
    ) -> None:
        """
        Quantize a model using llama.cpp quantize
        Args:
            input_path: Path to input GGUF model
            output_path: Path to write quantized model
            quant_type: Quantization type (default q4_k_m)
        """
        args = [
            str(self.quantize_binary),
            str(input_path),
            str(output_path),
            quant_type
        ]
        
        logger.info(
            "Quantizing model",
            input=str(input_path),
            output=str(output_path),
            type=quant_type
        )
        
        result = subprocess.run(
            args,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Quantization failed: {result.stderr}"
            )
        
        logger.info(
            "Quantization complete",
            output=str(output_path)
        )
    
    def validate_identity(self) -> bool:
        """Validate model identity and capabilities"""
        # TODO: Implement validation of:
        # - Special token presence
        # - Chat template validation
        # - Basic completion test
        return True