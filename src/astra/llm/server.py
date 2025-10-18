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
        """
        self.model_path = model_path
        self.grammar_path = grammar_path
        self.lora_paths = lora_paths or []
        self.host = host
        self.port = port
        
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