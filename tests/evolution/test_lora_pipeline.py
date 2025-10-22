"""Tests for LoRA evolution pipeline."""

import pytest
from pathlib import Path
import torch
import numpy as np
from evolution.lora.pipeline import (
    LoRAEvolutionPipeline,
    PipelineConfig,
    LoRAStageConfig
)
from evolution.gguf.patcher import GGUFPatcher, ValidationResult

@pytest.fixture
def test_pipeline_config(tmp_path, sample_model_path):
    """Create test pipeline configuration."""
    output_dir = tmp_path / "evolved"
    
    planner_lora = tmp_path / "planner.gguf"
    tooluse_lora = tmp_path / "tooluse.gguf"
    safety_lora = tmp_path / "safety.gguf"
    
    # Create mock LoRA files
    for lora in [planner_lora, tooluse_lora, safety_lora]:
        lora.write_bytes(sample_model_path.read_bytes())
    
    stages = [
        LoRAStageConfig(
            name="Planner",
            lora_path=planner_lora,
            acceptance_criteria={"acc": 0.97}
        ),
        LoRAStageConfig(
            name="ToolUse",
            lora_path=tooluse_lora,
            acceptance_criteria={"acc": 0.90}
        ),
        LoRAStageConfig(
            name="Safety",
            lora_path=safety_lora,
            acceptance_criteria={"acc": 0.98}
        )
    ]
    
    config = PipelineConfig(
        base_model_path=sample_model_path,
        output_dir=output_dir,
        stages=stages,
        global_criteria={"drift": 0.07},
        quantization="Q5_K_M",
        rope_scale=1.2
    )
    
    return config

@pytest.fixture
def mock_patcher(mocker):
    """Create mock GGUFPatcher."""
    patcher = mocker.Mock(spec=GGUFPatcher)
    
    # Mock validation results
    def mock_validate(*args, **kwargs):
        return ValidationResult(
            ppl=8.5,
            acc=0.98,
            drift=0.05,
            logs=["Validation successful"]
        )
    
    patcher.validate.side_effect = mock_validate
    
    # Mock preview and patch
    patcher.patch_preview.return_value.snapshot_id = "test-snapshot-1"
    patcher.patch_and_save.return_value = "test-snapshot-2"
    
    return patcher

@pytest.fixture
def pipeline(test_pipeline_config, mock_patcher, mocker):
    """Create LoRA evolution pipeline instance."""
    pipeline = LoRAEvolutionPipeline(test_pipeline_config)
    pipeline.patcher = mock_patcher
    return pipeline


class TestLoRAEvolutionPipeline:
    """Test LoRA evolution pipeline."""
    
    def test_pipeline_initialization(self, pipeline, test_pipeline_config):
        """Test pipeline initialization."""
        assert pipeline.config == test_pipeline_config
        assert (pipeline.config.output_dir / "snapshots").exists()
        assert (pipeline.config.output_dir / "checkpoints").exists()
        
    def test_successful_evolution(self, pipeline):
        """Test successful evolution through all stages."""
        evolved_path = pipeline.evolve()
        
        # Verify all stages were processed
        assert pipeline.patcher.patch_and_save.call_count == len(pipeline.config.stages) + 1
        assert evolved_path == pipeline.config.output_dir / "final.gguf"
        
    def test_validation_failure(self, pipeline, mock_patcher):
        """Test evolution with validation failure."""
        # Make second stage fail validation
        def mock_validate(*args, **kwargs):
            if mock_validate.calls == 1:  # Second call
                return ValidationResult(
                    ppl=12.0,  # High perplexity
                    acc=0.85,  # Below threshold
                    drift=0.08,  # Above threshold
                    logs=["Validation failed"]
                )
            return ValidationResult(
                ppl=8.5,
                acc=0.98,
                drift=0.05,
                logs=["Validation successful"]
            )
            
        mock_validate.calls = 0
        mock_patcher.validate.side_effect = mock_validate
        
        with pytest.raises(ValueError, match=".*failed.*check"):
            pipeline.evolve()
            
        # Verify pipeline stopped after failure
        assert mock_patcher.patch_and_save.call_count == 1
        
    def test_tensor_compatibility(self, pipeline, mock_patcher, mocker):
        """Test tensor compatibility checking."""
        # Mock tensor loading
        mock_patcher._load_tensors.return_value = {
            "test_tensor": torch.randn(10, 10)
        }
        
        evolved_path = pipeline.evolve()
        assert mock_patcher._load_tensors.call_count == len(pipeline.config.stages) * 2
        
    def test_quantization_and_rope(self, pipeline):
        """Test final quantization and RoPE adjustment."""
        evolved_path = pipeline.evolve()
        
        # Verify final transformation
        final_call = pipeline.patcher.patch_and_save.call_args
        assert final_call.kwargs["ops"] == {
            "quantize": "Q5_K_M",
            "rope_scale": 1.2
        }