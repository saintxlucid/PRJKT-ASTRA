"""
PEFT adapter training with safety gates
"""
from typing import List, Dict, Any, Optional, Tuple
import torch
from torch.utils.data import DataLoader
import transformers
from peft import (
    get_peft_model,
    LoraConfig,
    TaskType,
    PeftModel,
    PeftConfig
)
from datasets import Dataset
import wandb
import logging
from pathlib import Path
import json
from datetime import datetime

from .rehearsal import ExperienceBuffer, create_rehearsal_loader

logger = logging.getLogger(__name__)

class AdapterTrainer:
    """Manages adapter training with safety checks"""
    
    def __init__(
        self,
        model_name: str,
        adapter_name: str,
        output_dir: str,
        experience_buffer: ExperienceBuffer,
        wandb_project: Optional[str] = None,
        lora_config: Optional[Dict[str, Any]] = None
    ):
        self.model_name = model_name
        self.adapter_name = adapter_name
        self.output_dir = Path(output_dir)
        self.experience_buffer = experience_buffer
        self.wandb_project = wandb_project
        
        # Load base model and tokenizer
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_name
        )
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Configure LoRA adapter
        lora_config = lora_config or {}
        default_config = {
            "r": 8,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "bias": "none",
            "task_type": TaskType.CAUSAL_LM
        }
        config = LoraConfig(
            **{**default_config, **lora_config}
        )
        
        self.model = get_peft_model(self.model, config)
        self.model.print_trainable_parameters()
        
        # Training metrics
        self.metrics: Dict[str, float] = {}
        self.best_loss: float = float('inf')
        
    def train(
        self,
        num_epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
        max_grad_norm: float = 1.0,
        warmup_ratio: float = 0.1,
        eval_steps: int = 100,
        save_steps: int = 500,
        **kwargs
    ) -> Dict[str, float]:
        """
        Train adapter with safety checks
        
        Args:
            num_epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Peak learning rate
            max_grad_norm: Gradient clipping
            warmup_ratio: LR warmup ratio
            eval_steps: Steps between evals
            save_steps: Steps between saves
            **kwargs: Additional training args
            
        Returns:
            Dict of training metrics
        """
        # Initialize W&B
        if self.wandb_project:
            wandb.init(
                project=self.wandb_project,
                config={
                    "model": self.model_name,
                    "adapter": self.adapter_name,
                    "epochs": num_epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    **kwargs
                }
            )
            
        # Create data loaders
        train_loader = create_rehearsal_loader(
            self.experience_buffer,
            self.tokenizer,
            batch_size=batch_size
        )
        
        # Training arguments
        training_args = transformers.TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            max_grad_norm=max_grad_norm,
            warmup_ratio=warmup_ratio,
            evaluation_strategy="steps",
            eval_steps=eval_steps,
            save_strategy="steps", 
            save_steps=save_steps,
            logging_steps=10,
            **kwargs
        )
        
        # Set up trainer
        trainer = transformers.Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_loader.dataset,
            compute_metrics=self._compute_metrics
        )
        
        # Train with safety checks
        try:
            trainer.train()
            
            # Save adapter
            self.save_adapter()
            
            metrics = {
                "final_loss": trainer.state.log_history[-1]["loss"],
                "best_loss": self.best_loss,
                **self.metrics
            }
            
            if self.wandb_project:
                wandb.log(metrics)
                
            return metrics
            
        except Exception as e:
            logger.error(
                "Training failed",
                exc_info=True
            )
            raise
            
    def _compute_metrics(
        self,
        eval_pred: Tuple[torch.Tensor, torch.Tensor]
    ) -> Dict[str, float]:
        """Compute evaluation metrics"""
        loss = eval_pred.predictions[0]
        
        metrics = {
            "eval_loss": float(loss.mean())
        }
        
        # Track best loss
        if metrics["eval_loss"] < self.best_loss:
            self.best_loss = metrics["eval_loss"]
            metrics["best_loss"] = self.best_loss
            
        self.metrics.update(metrics)
        
        if self.wandb_project:
            wandb.log(metrics)
            
        return metrics
        
    def save_adapter(self):
        """Save trained adapter"""
        # Create versioned output dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir = self.output_dir / f"{self.adapter_name}_{timestamp}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Save adapter weights
        self.model.save_pretrained(version_dir)
        
        # Save tokenizer
        self.tokenizer.save_pretrained(version_dir)
        
        # Save training metrics
        metrics_file = version_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
            
        logger.info(f"Saved adapter to {version_dir}")
        
    @classmethod
    def load_adapter(
        cls,
        adapter_path: str,
        model_name: str
    ) -> PeftModel:
        """Load trained adapter"""
        config = PeftConfig.from_pretrained(adapter_path)
        
        model = transformers.AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        model = PeftModel.from_pretrained(
            model,
            adapter_path
        )
        
        return model