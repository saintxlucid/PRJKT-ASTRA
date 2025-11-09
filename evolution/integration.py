"""Integration layer for ASTRA evolution system.

Provides unified interface for:
- LoRA merging with validation
- Schema enforcement
- RoPE tuning
- Policy enforcement
- Memory-aware planning
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .core.advanced import DeltaAnalyzer
from .core.schema import PlanSchema, ToolSchema, ResponseSchema
from .core.validation import ValidationResult
from .core.instrumentation import ModelInstrumentationData
from .core.loader import load_model
from .core.saver import save_model

from .rope import RoPEAnalyzer, RoPEConfig, RoPETuner
from .memory import MemoryManager, MemoryAwarePlanner, MemorySource
from .security import PolicyEngine, SecurityToken, SecurityLevel
from .monitoring import MonitoringManager
from .lora import merge_loras


@dataclass
class EvolutionConfig:
    """Configuration for evolution system."""
    workspace_path: Path
    policy_config: Path
    hmac_key: bytes
    embedding_dim: int = 768
    rope_scale: float = 1.2
    min_confidence: float = 0.7
    monitoring_port: int = 9090
    log_path: Optional[Path] = None


class EvolutionManager:
    """Central manager for ASTRA evolution system."""
    
    def __init__(self, config: EvolutionConfig):
        """Initialize evolution manager.
        
        Args:
            config: Evolution configuration
        """
        self.config = config
        self.workspace = Path(config.workspace_path)
        
        # Setup logging
        self.logger = logging.getLogger("evolution")
        
        # Initialize components
        self.policy = PolicyEngine(
            config.policy_config,
            config.hmac_key
        )
        
        self.memory = MemoryManager(
            embedding_dim=config.embedding_dim,
            min_confidence=config.min_confidence
        )
        
        self.planner = MemoryAwarePlanner(
            self.memory,
            min_confidence=config.min_confidence
        )
        
        # Initialize monitoring
        self.monitoring = MonitoringManager(
            port=config.monitoring_port,
            log_path=config.log_path
        )
        
    def merge_lora(
        self,
        base_model: Path,
        loras: List[Path],
        token: SecurityToken,
        context: Optional[Dict] = None
    ) -> Path:
        """Merge LoRA adapters with base model.
        
        Args:
            base_model: Base model path
            loras: List of LoRA paths
            token: Security token
            context: Optional operation context
            
        Returns:
            Path to merged model
        """
        # Start monitoring
        metric_ctx = self.monitoring.track_operation(
            "merge_lora",
            model=base_model.name,
            loras=len(loras)
        )
        
        try:
            # Validate operation
            self.policy.validate_operation(
                "model.merge_lora",
                token=token,
                context=context
            )
            
            # Create plan
            plan = self.planner.create_plan(
                f"Merge {len(loras)} LoRAs into {base_model.name}",
                requirements=["validation", "rollback"]
            )
            
            if not self.planner.validate_plan(plan):
                raise ValueError("Invalid merge plan")
                
            # Record operation in memory
            self.memory.add_memory(
                f"LoRA merge operation on {base_model.name}",
                MemorySource.TOOL_USE,
                metadata={"loras": str([str(p) for p in loras])}
            )
            
            # Track model sizes
            self.monitoring.track_model_size(
                base_model,
                "base"
            )
            for lora in loras:
                self.monitoring.track_model_size(
                    lora,
                    "lora"
                )
            
            # Execute merge
            merged_path = merge_loras(base_model, loras)
            
            # Track merged model size
            self.monitoring.track_model_size(
                merged_path,
                "merged"
            )
            
            # Record success
            self.memory.add_memory(
                f"Successfully merged LoRAs into {merged_path.name}",
                MemorySource.TOOL_USE
            )
            
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="success"
            )
            
            return merged_path
            
        except Exception as e:
            # Record failure
            self.memory.add_memory(
                f"Failed to merge LoRAs: {str(e)}",
                MemorySource.TOOL_USE,
                metadata={"error": str(e)}
            )
            
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="failure"
            )
            
            raise
            
    def tune_rope(
        self,
        model_path: Path,
        target_scale: float,
        token: SecurityToken,
        context: Optional[Dict] = None
    ) -> Path:
        """Tune RoPE parameters of model.
        
        Args:
            model_path: Model to tune
            target_scale: Target RoPE scale
            token: Security token
            context: Optional operation context
            
        Returns:
            Path to tuned model
        """
        # Start monitoring
        metric_ctx = self.monitoring.track_operation(
            "tune_rope",
            model=model_path.name,
            target_scale=target_scale
        )
        
        try:
            # Validate operation
            self.policy.validate_operation(
                "model.tune_rope",
                token=token,
                context=context
            )
            
            # Create plan
            plan = self.planner.create_plan(
                f"Tune RoPE scale to {target_scale} for {model_path.name}",
                requirements=["validation"]
            )
            
            if not self.planner.validate_plan(plan):
                raise ValueError("Invalid tuning plan")
                
            # Record operation
            self.memory.add_memory(
                f"RoPE tuning operation on {model_path.name}",
                MemorySource.TOOL_USE,
                metadata={"target_scale": str(target_scale)}
            )
            
            # Track initial model size
            self.monitoring.track_model_size(
                model_path,
                "original"
            )
            
            # Execute tuning
            tuner = RoPETuner(model_path)
            config = RoPEConfig(target_scale=target_scale)
            
            # Load model tensors
            tensors = load_model(model_path)
            
            # Tune RoPE
            result = tuner.tune_model(tensors, config, dry_run=False)
            
            if not result.success:
                raise ValueError(f"Tuning failed: {result.message}")
                
            # Save tuned model
            tuned_path = model_path.parent / f"{model_path.stem}_tuned.bin"
            save_model(result.modified_tensors, tuned_path)
            
            # Track tuned model size
            self.monitoring.track_model_size(
                tuned_path,
                "tuned"
            )
            
            # Record success
            self.memory.add_memory(
                f"Successfully tuned RoPE parameters in {tuned_path.name}",
                MemorySource.TOOL_USE,
                metadata={
                    "scale": str(target_scale),
                    "metrics": str(result.metrics)
                }
            )
            
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="success"
            )
            
            return tuned_path
            
        except Exception as e:
            # Record failure
            self.memory.add_memory(
                f"Failed to tune RoPE parameters: {str(e)}",
                MemorySource.TOOL_USE,
                metadata={"error": str(e)}
            )
            
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="failure"
            )
            
            raise
            
    def validate_schema(
        self,
        content: str,
        schema_type: str,
        token: Optional[SecurityToken] = None,
        context: Optional[Dict] = None
    ) -> ValidationResult:
        """Validate content against schema.
        
        Args:
            content: Content to validate
            schema_type: Type of schema to use
            token: Optional security token
            context: Optional operation context
            
        Returns:
            Validation result
        """
        # Validate operation if token provided
        if token:
            self.policy.validate_operation(
                "schema.validate",
                token=token,
                context=context
            )
            
        # Select schema
        schema_map = {
            "plan": PlanSchema,
            "tool": ToolSchema,
            "response": ResponseSchema
        }
        
        schema_cls = schema_map.get(schema_type)
        if not schema_cls:
            raise ValueError(f"Unknown schema type: {schema_type}")
            
        # Record validation
        self.memory.add_memory(
            f"Schema validation for {schema_type}",
            MemorySource.TOOL_USE
        )
        
        try:
            # Validate
            schema = schema_cls.parse_raw(content)
            
            # Record success
            self.memory.add_memory(
                f"Successful schema validation",
                MemorySource.TOOL_USE
            )
            
            return ValidationResult(valid=True, message="Validation successful")
            
        except Exception as e:
            # Record failure
            self.memory.add_memory(
                f"Schema validation failed: {str(e)}",
                MemorySource.TOOL_USE,
                metadata={"error": str(e)}
            )
            
            return ValidationResult(
                valid=False,
                message=f"Validation failed: {str(e)}"
            )
            
    def create_plan(
        self,
        query: str,
        token: Optional[SecurityToken] = None,
        context: Optional[Dict] = None,
        requirements: Optional[List[str]] = None
    ) -> Dict:
        """Create memory-aware plan.
        
        Args:
            query: Planning query
            token: Optional security token
            context: Optional operation context
            requirements: Optional requirements
            
        Returns:
            Plan dictionary
        """
        # Start monitoring
        metric_ctx = self.monitoring.track_operation(
            "create_plan",
            query_length=len(query)
        )
        
        try:
            # Validate operation if token provided
            if token:
                self.policy.validate_operation(
                    "plan.create",
                    token=token,
                    context=context
                )
                
            # Create plan
            plan = self.planner.create_plan(
                query,
                requirements=requirements
            )
            
            # Track memory stats
            self.monitoring.track_memory_stats(
                total_entries=len(self.memory.get_all_memories()),
                coherence_score=plan.metadata.coherence_score
            )
            
            # Record planning
            self.memory.add_memory(
                f"Created plan for: {query}",
                MemorySource.PLAN,
                metadata={
                    "requirements": str(requirements or []),
                    "steps": str(len(plan.steps))
                }
            )
            
            result = {
                "steps": [
                    {
                        "description": step.description,
                        "citations": [
                            {"key": c.key, "context": c.context}
                            for c in step.citations
                        ],
                        "confidence": step.estimated_confidence
                    }
                    for step in plan.steps
                ],
                "metadata": {
                    "citations": len(plan.metadata.citations),
                    "coherence": plan.metadata.coherence_score,
                    "verified": all(plan.validation_status.values())
                }
            }
            
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="success"
            )
            
            return result
            
        except Exception as e:
            # Complete monitoring
            self.monitoring.complete_operation(
                metric_ctx,
                status="failure"
            )
            
            raise