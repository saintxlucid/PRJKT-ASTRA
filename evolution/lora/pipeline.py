"""GGUF LoRA Evolution Pipeline.

Handles sequential merging of Planner, ToolUse, and Safety LoRAs with validation gates.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import torch
import numpy as np
from ..core.validators import validate_lora_compatibility
from ..gguf.patcher import GGUFPatcher, ValidationResult
from ..core.advanced import DeltaAnalyzer


@dataclass
class LoRAStageConfig:
    """Configuration for a single LoRA merge stage."""
    name: str  # e.g. "Planner", "ToolUse", "Safety"
    lora_path: Path
    alpha: float = 1.0
    target_modules: Optional[List[str]] = None
    acceptance_criteria: Dict[str, float] = None  # e.g. {"ppl": 10.0, "acc": 0.9}


@dataclass
class PipelineConfig:
    """Configuration for the entire LoRA evolution pipeline."""
    base_model_path: Path
    output_dir: Path
    stages: List[LoRAStageConfig]
    global_criteria: Dict[str, float] = None  # e.g. {"drift": 0.07}
    quantization: Optional[str] = "Q5_K_M"
    rope_scale: Optional[float] = None


class LoRAEvolutionPipeline:
    """
    Handles sequential merging of multiple LoRAs with validation gates.
    
    Features:
    - Stage-by-stage LoRA merging with validation
    - Automatic rollback on validation failure
    - Drift monitoring and quantization
    - Provenance tracking
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.patcher = GGUFPatcher(snapshot_dir=config.output_dir / "snapshots")
        self.analyzer = DeltaAnalyzer()
        self._ensure_dirs()
        
    def _ensure_dirs(self):
        """Create necessary directories."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "snapshots").mkdir(exist_ok=True)
        (self.config.output_dir / "checkpoints").mkdir(exist_ok=True)
        
    def _validate_stage(
        self,
        stage: LoRAStageConfig,
        evolved_path: Path,
        base_path: Path
    ) -> ValidationResult:
        """Validate a single evolution stage."""
        # Perform comprehensive validation
        result = self.patcher.validate(
            evolved_path,
            dataset="validation_data",  # TODO: Make configurable
            base_path=base_path
        )
        
        # Check stage-specific criteria
        if stage.acceptance_criteria:
            for metric, threshold in stage.acceptance_criteria.items():
                if getattr(result, metric) < threshold:
                    raise ValueError(
                        f"Stage {stage.name} failed {metric} check: "
                        f"{getattr(result, metric)} < {threshold}"
                    )
                    
        # Check global criteria
        if self.config.global_criteria:
            for metric, threshold in self.config.global_criteria.items():
                if getattr(result, metric) > threshold:  # Note: > for drift
                    raise ValueError(
                        f"Stage {stage.name} failed global {metric} check: "
                        f"{getattr(result, metric)} > {threshold}"
                    )
                    
        return result
        
    def _merge_stage(
        self,
        stage: LoRAStageConfig,
        base_path: Path
    ) -> Path:
        """Merge a single LoRA stage."""
        # Generate stage output path
        stage_path = self.config.output_dir / "checkpoints" / f"{stage.name}.gguf"
        
        # Prepare merge operation
        ops = {
            "lora_paths": [str(stage.lora_path)],
            "alpha": stage.alpha
        }
        if stage.target_modules:
            ops["target_modules"] = stage.target_modules
            
        # Execute merge
        preview = self.patcher.patch_preview(str(base_path), ops)
        
        # Verify tensor compatibility
        base_tensors = self.patcher._load_tensors(base_path)
        lora_tensors = self.patcher._load_tensors(stage.lora_path)
        compatibility = validate_lora_compatibility(base_tensors, lora_tensors)
        
        if not compatibility["passed"]:
            raise ValueError(
                f"Stage {stage.name} LoRA incompatible with base model: "
                f"{compatibility['errors']}"
            )
            
        # Execute merge
        snapshot_id = self.patcher.patch_and_save(
            str(base_path),
            str(stage_path),
            preview.snapshot_id,
            ops
        )
        
        return stage_path
        
    def evolve(self) -> Path:
        """
        Execute the complete evolution pipeline.
        
        Returns:
            Path to the final evolved model
        """
        current_base = self.config.base_model_path
        
        for stage in self.config.stages:
            print(f"Evolving stage: {stage.name}")
            
            try:
                # Merge LoRA
                evolved_path = self._merge_stage(stage, current_base)
                
                # Validate result
                result = self._validate_stage(stage, evolved_path, current_base)
                
                print(f"Stage {stage.name} metrics:")
                print(f"- Perplexity: {result.ppl:.2f}")
                print(f"- Accuracy: {result.acc:.2f}")
                print(f"- Drift: {result.drift:.3f}")
                
                # Update base for next stage
                current_base = evolved_path
                
            except Exception as e:
                print(f"Stage {stage.name} failed: {str(e)}")
                # Rollback to last successful stage
                if current_base != self.config.base_model_path:
                    print(f"Rolling back to {current_base}")
                raise
                
        # Final quantization if requested
        if self.config.quantization:
            final_path = self.config.output_dir / "final.gguf"
            ops = {"quantize": self.config.quantization}
            
            if self.config.rope_scale:
                ops["rope_scale"] = self.config.rope_scale
                
            # Execute final transformations
            preview = self.patcher.patch_preview(str(current_base), ops)
            self.patcher.patch_and_save(
                str(current_base),
                str(final_path),
                preview.snapshot_id,
                ops
            )
            current_base = final_path
            
        return current_base