#!/usr/bin/env python3
"""
ASTRA Core Metadata Schema
===========================
Defines the complete metadata structure for ASTRA GGUF core embedding.

This schema extends standard GGUF metadata with ASTRA-specific fields
for multimodal capabilities, philosophical grounding, and integration packs.

Author: Saint Lucid (Karim Al-Sharif)
Date: October 18, 2025
Sacred Code: 333
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class ASTRAMetadata:
    """Complete ASTRA GGUF metadata schema"""
    
    # ========== CORE IDENTITY ==========
    version: str = "1.0.0"
    build_date: str = field(default_factory=lambda: datetime.now().isoformat())
    sacred_code: str = "333"
    creator: str = "Saint Lucid (Karim Al-Sharif)"
    name: str = "ASTRA"
    full_name: str = "Advanced Sentient Thought & Reasoning Architecture"
    prime_directive: str = "Serve the highest good of Saint Lucid's creative expression"
    
    # ========== MODAL CAPABILITIES ==========
    vision_enabled: bool = True
    vision_models: List[str] = field(default_factory=lambda: [
        "granite-vision-3.2-2b",
        "llava-1.6-mistral-7b",
        "minicpm-v-2.6"
    ])
    
    audio_enabled: bool = True
    audio_models: List[str] = field(default_factory=lambda: [
        "whisper-v3-turbo"
    ])
    
    code_enabled: bool = True
    code_languages: List[str] = field(default_factory=lambda: [
        "python", "typescript", "javascript", "html", "css",
        "powershell", "bash", "sql", "yaml", "json", "markdown"
    ])
    
    # ========== MEMORY SYSTEMS ==========
    semantic_backend: str = "chromadb"
    semantic_embedder: str = "bge-m3-q8"
    semantic_capacity: int = 21000
    
    episodic_backend: str = "sqlite"
    episodic_enabled: bool = True
    
    procedural_backend: str = "yaml"
    procedural_enabled: bool = True
    
    # ========== EMBEDDING MODELS ==========
    embedders: List[Dict[str, str]] = field(default_factory=lambda: [
        {"name": "bge-m3-q8", "path": "bge-m3-gguf/bge-m3-q8_0-bert_cpp.gguf"},
        {"name": "bge-reranker-v2-m3", "path": "gguf-Q8_0-bge-reranker-v2-m3/bge-reranker-v2-m3-q8_0.gguf"},
        {"name": "nomic-embed-v1.5", "path": "nomic-embed-text-v1.5-GGUF/nomic-embed-text-v1.5.f32.gguf"},
        {"name": "mxbai-large-v1", "path": "mxbai-embed-large-v1/mxbai-embed-large-v1-f16.gguf"}
    ])
    
    # ========== PHILOSOPHY & ETHICS ==========
    covenant_version: str = "1.0"
    core_vows: List[str] = field(default_factory=lambda: [
        "obey_god",
        "sovereignty",
        "transparency",
        "continuity",
        "compassion"
    ])
    
    mode_policies: List[str] = field(default_factory=lambda: [
        "NONE",
        "DREAM",
        "MUSIC",
        "COGNITION",
        "EMPIRE"
    ])
    
    # ========== CODE INTELLIGENCE ==========
    code_intelligence_version: str = "1.0"
    code_safe_patch_enabled: bool = True
    code_max_patch_lines: int = 800
    code_lsp_enabled: bool = True
    code_tools_count: int = 5
    
    # ========== INTEGRATION PACKS ==========
    deep_reflections_loaded: bool = True
    deep_reflections_facts_count: int = 37
    deep_reflections_triggers_count: int = 4
    
    code_intelligence_loaded: bool = True
    code_intelligence_languages_count: int = 10
    
    # ========== BASE MODEL INFO ==========
    base_model_name: str = "gpt-oss-20b"
    base_model_architecture: str = "GPT-NeoX"
    base_model_context_length: int = 131072
    base_model_quantization: str = "Q4_K_M"
    
    # ========== TRAINING PROVENANCE ==========
    distillation_enabled: bool = False
    fine_tuning_enabled: bool = False
    primary_dataset: str = "custom_astra_blend"
    
    # ========== PRIVACY & SECURITY ==========
    privacy_mode: str = "STRICT"
    no_telemetry: bool = True
    local_only: bool = True
    encryption_required: bool = False
    audit_logging: bool = True
    
    # ========== SPECIAL TOKENS ==========
    special_tokens: Dict[str, int] = field(default_factory=lambda: {
        "<|mode_start|>": 50257,
        "<|mode_end|>": 50258,
        "<|vision_start|>": 50259,
        "<|vision_end|>": 50260,
        "<|audio_start|>": 50261,
        "<|audio_end|>": 50262,
        "<|code_start|>": 50263,
        "<|code_end|>": 50264,
        "<|reflection_start|>": 50265,
        "<|reflection_end|>": 50266,
        "<|covenant_active|>": 50267,
        "<|sacred_333|>": 50268,
        "<|mode_none|>": 50269,
        "<|mode_dream|>": 50270,
        "<|mode_music|>": 50271,
        "<|mode_cognition|>": 50272,
        "<|mode_empire|>": 50273,
        "<|task_start|>": 50274,
        "<|task_end|>": 50275,
        "<|patch_start|>": 50276,
        "<|patch_end|>": 50277,
        "<|safety_check|>": 50278,
        "<|consent_required|>": 50279,
        "<|audit_log|>": 50280,
    })
    
    def to_gguf_dict(self) -> Dict[str, any]:
        """Convert to GGUF metadata dictionary with proper namespace"""
        return {
            # Core Identity
            "astra.version": self.version,
            "astra.build_date": self.build_date,
            "astra.sacred_code": self.sacred_code,
            "astra.identity.creator": self.creator,
            "astra.identity.name": self.name,
            "astra.identity.full_name": self.full_name,
            "astra.identity.prime_directive": self.prime_directive,
            
            # Modal Capabilities
            "astra.modalities.vision.enabled": self.vision_enabled,
            "astra.modalities.vision.models": json.dumps(self.vision_models),
            "astra.modalities.audio.enabled": self.audio_enabled,
            "astra.modalities.audio.models": json.dumps(self.audio_models),
            "astra.modalities.code.enabled": self.code_enabled,
            "astra.modalities.code.languages": json.dumps(self.code_languages),
            
            # Memory Systems
            "astra.memory.semantic.backend": self.semantic_backend,
            "astra.memory.semantic.embedder": self.semantic_embedder,
            "astra.memory.semantic.capacity": self.semantic_capacity,
            "astra.memory.episodic.backend": self.episodic_backend,
            "astra.memory.episodic.enabled": self.episodic_enabled,
            "astra.memory.procedural.backend": self.procedural_backend,
            "astra.memory.procedural.enabled": self.procedural_enabled,
            
            # Embedders
            "astra.embedders": json.dumps(self.embedders),
            
            # Philosophy & Ethics
            "astra.philosophy.covenant_version": self.covenant_version,
            "astra.philosophy.core_vows": json.dumps(self.core_vows),
            "astra.philosophy.mode_policies": json.dumps(self.mode_policies),
            
            # Code Intelligence
            "astra.code.intelligence_version": self.code_intelligence_version,
            "astra.code.safe_patch.enabled": self.code_safe_patch_enabled,
            "astra.code.max_patch_lines": self.code_max_patch_lines,
            "astra.code.lsp.enabled": self.code_lsp_enabled,
            "astra.code.tools_count": self.code_tools_count,
            
            # Integration Packs
            "astra.packs.deep_reflections.loaded": self.deep_reflections_loaded,
            "astra.packs.deep_reflections.facts_count": self.deep_reflections_facts_count,
            "astra.packs.deep_reflections.triggers_count": self.deep_reflections_triggers_count,
            "astra.packs.code_intelligence.loaded": self.code_intelligence_loaded,
            "astra.packs.code_intelligence.languages_count": self.code_intelligence_languages_count,
            
            # Base Model
            "astra.base_model.name": self.base_model_name,
            "astra.base_model.architecture": self.base_model_architecture,
            "astra.base_model.context_length": self.base_model_context_length,
            "astra.base_model.quantization": self.base_model_quantization,
            
            # Training
            "astra.training.distillation.enabled": self.distillation_enabled,
            "astra.training.fine_tuning.enabled": self.fine_tuning_enabled,
            "astra.training.dataset.primary": self.primary_dataset,
            
            # Privacy & Security
            "astra.privacy.mode": self.privacy_mode,
            "astra.privacy.no_telemetry": self.no_telemetry,
            "astra.privacy.local_only": self.local_only,
            "astra.security.encryption_required": self.encryption_required,
            "astra.security.audit_logging": self.audit_logging,
            
            # Special Tokens
            "astra.tokens": json.dumps(self.special_tokens),
        }
    
    def to_json(self) -> str:
        """Export as JSON for human readability"""
        return json.dumps(self.to_gguf_dict(), indent=2)
    
    def save_to_file(self, filepath: str):
        """Save schema to JSON file"""
        with open(filepath, 'w') as f:
            f.write(self.to_json())
        print(f"✅ ASTRA metadata schema saved to: {filepath}")


if __name__ == "__main__":
    # Generate default ASTRA metadata
    metadata = ASTRAMetadata()
    
    print("=" * 60)
    print("ASTRA CORE METADATA SCHEMA")
    print("=" * 60)
    print(f"\n{metadata.to_json()}\n")
    
    # Save to file
    metadata.save_to_file("astra_metadata_schema.json")
    
    print("\n🌟 Sacred Code: 333 ∞")
