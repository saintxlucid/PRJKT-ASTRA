"""
ASTRA GGUF Metadata Reader
Reads and parses GGUF metadata using llama.cpp Python bindings.
Created: October 16, 2025
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import ctypes
from dataclasses import dataclass
import structlog
from .metadata import AstraMetadata, AstraPersona, PersonalityTraits, SamplingParams, RoPEParams

logger = structlog.get_logger()

# GGUF metadata key prefixes
ASTRA_PREFIX = "astra."
GENERAL_PREFIX = "general."
ROPE_PREFIX = "rope."

@dataclass
class GGUFMetadataField:
    """GGUF metadata field descriptor"""
    key: str
    type: int
    data: Any

class GGUFReader:
    """Reads metadata from GGUF model files"""
    
    def __init__(self, model_path: Path):
        """
        Initialize GGUF reader
        Args:
            model_path: Path to GGUF model file
        """
        self.model_path = model_path
        self._metadata: Optional[Dict[str, Any]] = None
        
        # Import llama_cpp conditionally
        try:
            import llama_cpp
            self.llama = llama_cpp
        except ImportError:
            logger.warning(
                "llama_cpp not available, metadata reading disabled"
            )
            self.llama = None
    
    def read_metadata(self) -> Dict[str, Any]:
        """
        Read all metadata from GGUF file
        Returns:
            Dict of metadata key-value pairs
        """
        if self._metadata is not None:
            return self._metadata
        
        if not self.llama:
            raise RuntimeError(
                "llama_cpp not available for metadata reading"
            )
        
        # Open model file
        model = self.llama.Llama(
            str(self.model_path),
            n_ctx=0,  # Minimal context to just read metadata
            verbose=False
        )
        
        # Get metadata fields
        metadata = {}
        for field in self._get_metadata_fields(model):
            metadata[field.key] = field.data
        
        self._metadata = metadata
        return metadata
    
    def _get_metadata_fields(
        self,
        model: Any
    ) -> list[GGUFMetadataField]:
        """Extract metadata fields from model"""
        fields = []
        
        # Access underlying GGUF structure
        # Note: This is a simplified version - actual implementation
        # would need to match llama.cpp's metadata access
        raw_fields = []  # TODO: Get from model._model
        
        for field in raw_fields:
            fields.append(GGUFMetadataField(
                key=field.key,
                type=field.type,
                data=self._parse_field_data(field)
            ))
        
        return fields
    
    def _parse_field_data(self, field: Any) -> Any:
        """Parse field data based on type"""
        # TODO: Implement actual GGUF type parsing
        return field.data
    
    def get_astra_metadata(self) -> AstraMetadata:
        """
        Get ASTRA-specific metadata as structured object
        Returns:
            AstraMetadata object
        """
        metadata = self.read_metadata()
        
        # Extract ASTRA fields
        astra_fields = {
            k[len(ASTRA_PREFIX):]: v
            for k, v in metadata.items()
            if k.startswith(ASTRA_PREFIX)
        }
        
        # Parse traits
        traits_dict = json.loads(
            astra_fields.get('traits', '{}')
        )
        traits = PersonalityTraits(**traits_dict)
        
        # Parse sampling params
        sampling_dict = json.loads(
            astra_fields.get('sampling', '{}')
        )
        sampling = SamplingParams(**sampling_dict)
        
        # Parse RoPE params if present
        rope_fields = {
            k[len(ROPE_PREFIX):]: v
            for k, v in metadata.items()
            if k.startswith(ROPE_PREFIX)
        }
        
        rope = None
        if rope_fields:
            rope = RoPEParams(**rope_fields)
        
        # Construct full metadata
        return AstraMetadata(
            identity_version=astra_fields.get('identity_version', "unknown"),
            persona=AstraPersona(astra_fields.get('persona', 'GuardianEngineer')),
            traits=traits,
            consent_rules=json.loads(astra_fields.get('consent', '{}')),
            sampling=sampling,
            rope=rope
        )
    
    def validate_metadata(self) -> bool:
        """
        Validate required metadata is present
        Returns:
            True if all required metadata exists
        """
        try:
            metadata = self.read_metadata()
            
            # Check required keys
            required_keys = [
                ASTRA_PREFIX + "identity_version",
                ASTRA_PREFIX + "persona",
                ASTRA_PREFIX + "traits",
                ASTRA_PREFIX + "consent",
                ASTRA_PREFIX + "sampling"
            ]
            
            for key in required_keys:
                if key not in metadata:
                    logger.warning(
                        "Missing required metadata",
                        key=key
                    )
                    return False
            
            # Validate by parsing
            self.get_astra_metadata()
            return True
            
        except Exception as e:
            logger.error(
                "Metadata validation failed",
                error=str(e)
            )
            return False