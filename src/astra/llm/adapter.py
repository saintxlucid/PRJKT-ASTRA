"""
ASTRA Model Adaptation Pipeline
Handles LoRA training, GGUF export, and quantization.
Created: October 16, 2025
"""
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import json
import torch
from transformers import (
    AutoTokenizer, AutoModelForCausalLM,
    TrainingArguments, Trainer
)
from peft import (
    LoraConfig, get_peft_model,
    PeftModel, TaskType
)
from datasets import Dataset
import structlog
from .metadata import AstraMetadata
from .chat import ASTRA_TOKENS, ChatManager

logger = structlog.get_logger()

class ModelAdapter:
    """Handles model adaptation and training"""
    
    def __init__(
        self,
        base_model_path: str,
        output_dir: Path,
        metadata: AstraMetadata
    ):
        """
        Initialize model adapter
        Args:
            base_model_path: HuggingFace model ID or path
            output_dir: Output directory for artifacts
            metadata: ASTRA metadata to embed
        """
        self.base_model_path = base_model_path
        self.output_dir = output_dir
        self.metadata = metadata
        
        # Create output directories
        self.lora_dir = output_dir / "lora"
        self.hf_dir = output_dir / "hf_model"
        self.gguf_dir = output_dir / "gguf"
        
        for d in [self.lora_dir, self.hf_dir, self.gguf_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_path,
            use_fast=True
        )
        
        logger.info(
            "Initialized model adapter",
            base_model=base_model_path,
            output_dir=str(output_dir)
        )
    
    def prepare_tokenizer(self):
        """Add ASTRA special tokens and resize model embeddings"""
        # Add special tokens
        new_tokens = self.tokenizer.add_special_tokens({
            "additional_special_tokens": ASTRA_TOKENS
        })
        
        logger.info(
            "Added special tokens",
            count=new_tokens
        )
        
        # Save special tokens
        tokens_path = self.output_dir / "tokens.json"
        with open(tokens_path, 'w') as f:
            json.dump({
                "additional_special_tokens": ASTRA_TOKENS
            }, f, indent=2)
        
        # Save chat template
        template_path = self.output_dir / "chat_template.jinja"
        chat_manager = ChatManager()
        chat_manager.export_template(template_path)
    
    def train_lora(
        self,
        train_data: Union[Dataset, Path],
        lora_config: Optional[Dict[str, Any]] = None,
        training_args: Optional[Dict[str, Any]] = None
    ):
        """
        Train LoRA adapter
        Args:
            train_data: HF Dataset or path to JSON data
            lora_config: LoRA configuration overrides
            training_args: Training arguments overrides
        """
        # Load dataset if path provided
        if isinstance(train_data, Path):
            with open(train_data) as f:
                data = json.load(f)
            train_data = Dataset.from_dict(data)
        
        # Default LoRA config
        default_lora = {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": [
                "q_proj", "k_proj", "v_proj",
                "o_proj", "gate_proj",
                "up_proj", "down_proj"
            ],
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": TaskType.CAUSAL_LM
        }
        lora_config = {**default_lora, **(lora_config or {})}
        
        # Default training args
        default_args = {
            "output_dir": str(self.lora_dir),
            "num_train_epochs": 3,
            "per_device_train_batch_size": 4,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "logging_steps": 10,
            "save_steps": 100,
            "save_total_limit": 3,
        }
        training_args = TrainingArguments(
            **{**default_args, **(training_args or {})}
        )
        
        # Load base model
        logger.info("Loading base model")
        model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Resize embeddings for new tokens
        model.resize_token_embeddings(len(self.tokenizer))
        
        # Initialize LoRA
        logger.info("Initializing LoRA", config=lora_config)
        lora_config = LoraConfig(**lora_config)
        model = get_peft_model(model, lora_config)
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_data,
            tokenizer=self.tokenizer
        )
        
        # Train
        logger.info("Starting LoRA training")
        trainer.train()
        
        # Save adapter
        model.save_pretrained(self.lora_dir)
        logger.info("Saved LoRA adapter", path=str(self.lora_dir))
    
    def merge_and_export(self):
        """Merge LoRA and export to GGUF"""
        # Load base model
        logger.info("Loading base model for merge")
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=torch.float16
        )
        base_model.resize_token_embeddings(len(self.tokenizer))
        
        # Load and merge LoRA
        logger.info("Loading LoRA adapter")
        model = PeftModel.from_pretrained(
            base_model,
            self.lora_dir
        )
        
        logger.info("Merging LoRA weights")
        model = model.merge_and_unload()
        
        # Save merged model
        logger.info("Saving merged model")
        model.save_pretrained(self.hf_dir)
        self.tokenizer.save_pretrained(self.hf_dir)
        
        # Export to GGUF
        self._export_gguf()
    
    def _export_gguf(self):
        """Export to GGUF format"""
        # Prepare metadata arguments
        metadata_args = [
            "--metadata", f"general.name={self.metadata.identity_version}",
            "--metadata", f"astra.identity_version={self.metadata.identity_version}",
            "--metadata", f"astra.persona={self.metadata.persona}",
            "--metadata", f"astra.traits={json.dumps(self.metadata.traits.dict())}",
            "--metadata", f"astra.consent={json.dumps(self.metadata.consent_rules)}",
            "--metadata", f"astra.sampling={json.dumps(self.metadata.sampling.dict())}"
        ]
        
        if self.metadata.rope:
            metadata_args.extend([
                "--metadata", f"rope.scaling={self.metadata.rope.scaling or 'none'}",
                "--metadata", f"rope.freq_base={self.metadata.rope.freq_base or 10000}"
            ])
        
        # Build conversion command
        convert_cmd = [
            "python3", "convert.py",
            "--model", str(self.hf_dir),
            "--outfile", str(self.gguf_dir / "model-f16.gguf"),
            "--chat-template", str(self.output_dir / "chat_template.jinja"),
            *metadata_args
        ]
        
        # Execute conversion (TODO: implement actual execution)
        logger.info(
            "Would execute GGUF conversion",
            cmd=" ".join(convert_cmd)
        )
        
        # Quantize
        quant_cmd = [
            "./quantize",
            str(self.gguf_dir / "model-f16.gguf"),
            str(self.gguf_dir / "model-q4_k_m.gguf"),
            "q4_k_m"
        ]
        
        logger.info(
            "Would execute quantization",
            cmd=" ".join(quant_cmd)
        )